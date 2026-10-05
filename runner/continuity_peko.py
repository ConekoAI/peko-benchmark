"""Isolated native Peko adapter for the continuity runner; never sees the oracle."""
from __future__ import annotations

import hashlib
import json
import math
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from continuity_usage import reconcile_usage


class PekoDriver:
    def __init__(self, run_dir: Path, timeout_secs: int, budget_usd: float):
        self.binary = None
        self.daemon = None
        self.run_dir = run_dir
        self.timeout_secs = timeout_secs
        self.budget_usd = budget_usd
        self.model_name = os.environ.get("PEKO_MODEL_NAME", "MiniMax-M3")
        self.model = os.environ.get("PEKO_MODEL_ID", self.model_name)
        self.api_format = os.environ.get("PEKO_API_FORMAT", "anthropic_messages")
        self.base_url = os.environ.get("PEKO_BASE_URL", "https://api.minimaxi.com/anthropic")
        self.principal = "continuity-bench"
        self.temp = None
        self.env = None
        self.pid = None
        self.deadline = None
        self.command_index = 0
        self.last_reply_id = None
        self.metadata = {}

    def _redact(self, text: str) -> str:
        for key in ("PEKO_API_KEY", "PEKO_MASTER_PASSPHRASE", "PEKO_IDENTITY_PASSPHRASE"):
            value = self.env.get(key, "") if self.env else ""
            if value:
                text = text.replace(value, "[REDACTED]")
        return text

    def _command(self, *args: str, cleanup: bool = False) -> str:
        remaining = 20 if cleanup else self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("scenario wall-clock budget exhausted")
        proc = subprocess.Popen([str(self.binary), *args], env=self.env,
                                cwd=self.temp.name, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
        try:
            command_limit = 330 if args[0] == "create" else 180
            stdout, stderr = proc.communicate(timeout=min(remaining, command_limit))
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
            self.command_index += 1
            (self.run_dir / f"command-{self.command_index:02}.log").write_text(
                self._redact(f"operation={args[0]} timeout=true\n{stdout}\n{stderr}"))
            raise TimeoutError(f"Peko {args[0]} exceeded command/scenario timeout")
        self.command_index += 1
        log = self.run_dir / f"command-{self.command_index:02}.log"
        log.write_text(self._redact(f"operation={args[0]} rc={proc.returncode}\n{stdout}\n{stderr}"))
        if proc.returncode:
            raise RuntimeError(f"Peko {args[0]} failed (rc={proc.returncode}); see {log.name}")
        return stdout

    def _ready(self):
        while time.monotonic() < self.deadline:
            try:
                status = json.loads(self._command("daemon", "status", "--json"))
                if status.get("ready") is True and status.get("running") is True:
                    self.pid = int((Path(self.temp.name) / ".peko/run/daemon.pid").read_text().strip())
                    return
            except (RuntimeError, ValueError, FileNotFoundError):
                pass
            time.sleep(0.2)
        raise TimeoutError("isolated daemon did not become ready")

    def start(self) -> dict:
        binary = os.environ.get("PEKO_BIN")
        if not binary or not Path(binary).is_file():
            raise ValueError("PEKO_BIN must name an existing peko CLI binary")
        self.binary = Path(binary).resolve()
        self.daemon = self.binary.with_name("peko-daemon")
        if not self.daemon.is_file():
            raise ValueError("build peko-daemon beside PEKO_BIN before benchmarking")
        if not os.environ.get("PEKO_API_KEY"):
            raise ValueError("PEKO_API_KEY is required for the isolated model catalog")
        self.deadline = time.monotonic() + self.timeout_secs
        # Keep Unix socket paths short; override paths only in child environments.
        self.temp = tempfile.TemporaryDirectory(prefix="pbc-", dir="/tmp")
        home = Path(self.temp.name)
        peko_home = home / ".peko"
        (peko_home / "run").mkdir(parents=True)
        self.env = dict(os.environ)
        self.env.update(HOME=str(home), USERPROFILE=str(home), PEKO_HOME=str(peko_home),
                        PEKO_CONFIG_DIR=str(peko_home), PEKO_DATA_DIR=str(peko_home / "data"),
                        PEKO_CACHE_DIR=str(peko_home / "cache"),
                        PEKO_DAEMON_SOCK=str(peko_home / "run/daemon.sock"), PEKO_DAEMON_PIPE="",
                        PEKO_MASTER_PASSPHRASE="continuity-bench-vault-passphrase",
                        PEKO_IDENTITY_PASSPHRASE="continuity-bench-vault-passphrase",
                        PEKO_UNLOCK_METHOD="passphrase")
        self.env.pop("PEKO_TEST_RESOLVER_BOOTSTRAP", None)
        model_args = ["model", "add", "--id", self.model, "--api-format", self.api_format,
                      "--base-url", self.base_url, "--model", self.model_name,
                      "--key", self.env["PEKO_API_KEY"]]
        for variable, flag in (("PEKO_MODEL_SPEC", "--spec"), ("PEKO_MODEL_COMPAT", "--compat"),
                               ("PEKO_CONTEXT_WINDOW", "--context-window"),
                               ("PEKO_MAX_OUTPUT_TOKENS", "--max-output-tokens")):
            if self.env.get(variable):
                model_args.extend([flag, self.env[variable]])
        self._command(*model_args)
        model = json.loads(self._command("model", "show", self.model, "--json"))
        (self.run_dir / "model.json").write_text(self._redact(json.dumps(model, indent=2)))
        pricing = (model.get("spec") or {}).get("pricing") or {}
        # Refuse unknown pricing before any model call; otherwise USD enforcement
        # can silently turn into a zero-cost counter. Token/request caps backstop it.
        rates = [pricing.get(k) for k in ("input_per_million", "output_per_million")]
        if any(not isinstance(x, (float, int)) or isinstance(x, bool)
               or not math.isfinite(x) or x < 0 for x in rates):
            raise ValueError("model needs both finite nonnegative pricing rates for a budgeted run")
        seed = home / "seed.toml"
        seed.write_text(f"name = {json.dumps(self.principal)}\n"
                        f"preferred_model_id = {json.dumps(self.model)}\n"
                        f"[quota]\nbudget_per_cycle = {self.budget_usd}\n"
                        "request_count = 100\ninput_tokens = 2000000\noutput_tokens = 50000\n")
        self.metadata = {"driver": "peko", "model": self.model, "wire_model": model.get("modelId"),
                "api_format": self.api_format, "base_url": self.base_url,
                "model_config": model, "pricing_hint": pricing,
                "cost_basis": self.env.get("PEKO_COST_BASIS", "runtime_pricing_hint"),
                "version": self._command("version").strip(), "budget_usd": self.budget_usd,
                "cli_sha256": hashlib.sha256(self.binary.read_bytes()).hexdigest(),
                "daemon_sha256": hashlib.sha256(self.daemon.read_bytes()).hexdigest(),
                "restart_kind": "process_restart", "initialization": "default_genesis",
                "initialization_completed": False}
        # Record setup metadata even when genesis fails after consuming tokens.
        self._command("create", self.principal, "--seed", str(seed), "--wait-timeout", "300")
        self._ready()
        self.metadata["initialization_completed"] = True
        return self.metadata

    def turn(self, message: str) -> str:
        prompt = Path(self.temp.name) / "event.txt"
        prompt.write_text(message)
        # Streaming stdout can contain pre-tool prose. Grade the persisted final
        # reply, never substring-search that stream for a valid-looking JSON object.
        self._command("send", self.principal, "--file", str(prompt), "--wait")
        log = json.loads(self._command("log", self.principal, "--limit", "1", "--json"))
        messages = log.get("messages", [])
        if len(messages) != 1:
            raise ValueError("no unique final channel reply after event")
        reply = messages[0]
        if ((reply.get("sender") or {}).get("kind") != "principal"
                or not isinstance(reply.get("text"), str)
                or not reply.get("id") or reply["id"] == self.last_reply_id):
            raise ValueError("latest channel entry is not a new principal reply")
        self.last_reply_id = reply["id"]
        return reply["text"]

    def _stop_owned_daemon(self):
        if self.pid is None:
            pid_file = Path(self.temp.name) / ".peko/run/daemon.pid"
            if not pid_file.exists():
                return
            self.pid = int(pid_file.read_text().strip())
        pid = self.pid
        try:
            # Use the Ctrl+C shutdown path; fall back only for this owned PID.
            os.kill(pid, signal.SIGINT)
        except ProcessLookupError:
            self._capture_daemon_log(pid)
            self.pid = None
            return "already_exited"
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                self._capture_daemon_log(pid)
                self.pid = None
                return "interrupt"
            time.sleep(0.1)
        # Only the PID from this adapter's isolated pidfile is eligible.
        os.kill(pid, signal.SIGKILL)
        self._capture_daemon_log(pid)
        self.pid = None
        return "forced"

    def _capture_daemon_log(self, pid):
        # The daemon opens a fresh log at startup. Preserve each epoch before
        # restarting, so initialization and shutdown diagnostics are not lost.
        log = Path(self.temp.name) / ".peko/logs/daemon.log"
        if log.is_file():
            (self.run_dir / f"daemon-{pid}.log").write_text(
                self._redact(log.read_text(errors="replace")))

    def restart(self) -> dict:
        previous = self.pid
        termination = self._stop_owned_daemon()
        self._command("daemon", "start", "--interval", "5")
        self._ready()
        return {"restart_verified": previous is not None and self.pid != previous,
                "previous_pid": previous, "current_pid": self.pid,
                "restart_kind": "process_restart", "termination": termination}

    def telemetry(self) -> dict:
        snapshot = json.loads(self._command("quota", "status", self.principal, "--json"))
        state = snapshot["state"]
        (self.run_dir / "quota.json").write_text(json.dumps(snapshot, indent=2))
        cache_rate = self.env.get("PEKO_CACHE_READ_USD_PER_MILLION")
        if cache_rate is not None:
            cache_rate = float(cache_rate)
            if not math.isfinite(cache_rate) or cache_rate < 0:
                raise ValueError("cache-read pricing rate must be finite and nonnegative")
        usage = reconcile_usage(Path(self.temp.name) / ".peko/data/principals" / self.principal,
                                state, self.metadata["pricing_hint"], cache_rate)
        (self.run_dir / "usage-reconciliation.json").write_text(json.dumps(usage, indent=2))
        return usage

    def close(self):
        if self.temp is not None:
            try:
                self._stop_owned_daemon()
            finally:
                try:
                    log = Path(self.temp.name) / ".peko/logs/daemon.log"
                    if log.is_file():
                        (self.run_dir / "daemon.log").write_text(
                            self._redact(log.read_text(errors="replace")))
                    # Preserve conversation evidence, not the vault or private keys.
                    peko_home = Path(self.temp.name) / ".peko"
                    for base in (peko_home / "principals", peko_home / "data"):
                        if not base.exists():
                            continue
                        for source in base.rglob("*.jsonl"):
                            if source.is_symlink():
                                continue
                            target = self.run_dir / "runtime-traces" / source.relative_to(peko_home)
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_text(self._redact(source.read_text(errors="replace")))
                finally:
                    self.temp.cleanup()
                    self.temp = None
