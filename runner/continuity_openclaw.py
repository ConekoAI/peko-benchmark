"""Native, isolated OpenClaw Gateway adapter. Receives current events only."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import shutil
import signal
import socket
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from continuity_proxy import AnthropicRelay


def export_transcripts(source: Path, target: Path, node: str, redact):
    """Export only canonical transcript rows; the database also holds auth tables."""
    with sqlite3.connect(source) as db:
        rows = db.execute("SELECT session_id, seq, event_json, event_zstd FROM transcript_events ORDER BY session_id, seq").fetchall()
    compressed = [base64.b64encode(row[3]).decode() for row in rows if row[2] is None]
    decoded = []
    if compressed:
        script = "const fs=require('node:fs'),z=require('node:zlib');const rows=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(rows.map(x=>z.zstdDecompressSync(Buffer.from(x,'base64')).toString('utf8'))));"
        decoded = json.loads(subprocess.check_output([node, "-e", script], input=json.dumps(compressed), text=True))
    index = 0
    records = []
    for session_id, seq, event_json, _ in rows:
        if event_json is None:
            event_json = decoded[index]
            index += 1
        records.append({"session_id": session_id, "seq": seq, "event": json.loads(event_json)})
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(redact("".join(json.dumps(r) + "\n" for r in records)))
    return records


def transcript_usage(records):
    usages = [r["event"]["message"]["usage"] for r in records
              if r["event"].get("type") == "message"
              and r["event"].get("message", {}).get("role") == "assistant"
              and r["event"]["message"].get("usage")]
    totals = {k: sum(u.get(k, 0) for u in usages) for k in ("input", "output", "cacheRead", "cacheWrite")}
    return {"request_count": len(usages), "uncached_input_tokens": totals["input"],
            "output_tokens": totals["output"], "cache_read_tokens": totals["cacheRead"],
            "cache_creation_tokens": totals["cacheWrite"]}


def final_reply(envelope: dict) -> str:
    result = envelope.get("result", envelope)
    if envelope.get("ok") is False or envelope.get("status") in {"error", "in_flight"}:
        raise ValueError("OpenClaw did not return a completed successful turn")
    if isinstance(result.get("final"), str):
        return result["final"]
    payloads = result.get("payloads", [])
    # Select the final assistant payload by position, never search for valid JSON.
    if not payloads or not isinstance(payloads[-1].get("text"), str):
        raise ValueError("OpenClaw has no final text payload")
    return payloads[-1]["text"]


class OpenClawDriver:
    def __init__(self, run_dir: Path, timeout_secs: int, budget_usd: float):
        self.run_dir, self.timeout_secs, self.budget_usd = run_dir, timeout_secs, budget_usd
        self.temp = self.env = self.process = self.relay = None
        self.log_handle = None
        self.metadata = {}
        self.command_index = 0
        self.epoch = 0

    def _redact(self, text):
        for value in (os.environ.get("PEKO_API_KEY"), os.environ.get("MIMO_API_KEY"),
                      self.relay.token if self.relay else None, getattr(self, "gateway_token", None)):
            if value:
                text = text.replace(value, "[REDACTED]")
        return text

    def _command(self, *args):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("scenario wall-clock budget exhausted")
        proc = subprocess.Popen([self.node, str(self.entry), *args], env=self.env,
                                cwd=self.temp.name, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                start_new_session=True)
        try:
            stdout, stderr = proc.communicate(timeout=min(remaining, 180))
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
            self._log_command(args, stdout, stderr, "timeout")
            raise TimeoutError(f"OpenClaw {args[0]} exceeded command/scenario timeout")
        self._log_command(args, stdout, stderr, proc.returncode)
        if proc.returncode:
            raise RuntimeError(f"OpenClaw {args[0]} failed (rc={proc.returncode}); see command-{self.command_index:02}.log")
        return stdout

    def _log_command(self, args, stdout, stderr, status):
        self.command_index += 1
        (self.run_dir / f"command-{self.command_index:02}.log").write_text(
            self._redact(f"operation={args[0]} rc={status}\n{stdout}\n{stderr}"))

    def start(self):
        entry = os.environ.get("OPENCLAW_ENTRY")
        if not entry or not Path(entry).is_file():
            raise ValueError("OPENCLAW_ENTRY must name the pinned installation's openclaw.mjs")
        key = os.environ.get("PEKO_API_KEY") or os.environ.get("MIMO_API_KEY")
        if not key:
            raise ValueError("PEKO_API_KEY or MIMO_API_KEY is required")
        if os.environ.get("PEKO_MODEL_NAME", "mimo-v2.6-flash") != "mimo-v2.6-flash":
            raise ValueError("this comparison profile requires mimo-v2.6-flash")
        self.entry = Path(entry).resolve()
        self.node = shutil.which("node")
        if not self.node:
            raise ValueError("Node.js is required")
        self.deadline = time.monotonic() + self.timeout_secs
        self.temp = tempfile.TemporaryDirectory(prefix="obc-", dir="/tmp")
        home = Path(self.temp.name)
        self.state = home / ".openclaw"
        self.state.mkdir(mode=0o700)
        self.workspace = self.state / "workspace"
        upstream = os.environ.get("PEKO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/anthropic")
        self.relay = AnthropicRelay(upstream, key, self.run_dir / "provider-calls.jsonl",
                                    self.deadline, self.budget_usd)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.gateway_token = secrets.token_hex(24)
        # Do not inherit other provider credentials, user settings, or shell-init
        # hooks. The real MiMo key stays in the relay, outside the agent process.
        self.env = {k: v for k, v in os.environ.items() if k in (
            "PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR", "TMPDIR")}
        self.env.update(HOME=str(home), USERPROFILE=str(home), OPENCLAW_HOME=str(home),
                        OPENCLAW_STATE_DIR=str(self.state), OPENCLAW_CONFIG_PATH=str(self.state / "openclaw.json"),
                        OPENCLAW_BENCH_PROVIDER_TOKEN=self.relay.token,
                        OPENCLAW_GATEWAY_TOKEN=self.gateway_token, NO_COLOR="1")
        model_ref = "mimo-benchmark/mimo-v2.6-flash"
        config = {"gateway": {"mode": "local", "port": self.port, "bind": "loopback",
                              "auth": {"mode": "token", "token": "${OPENCLAW_GATEWAY_TOKEN}"}},
                  "agents": {"defaults": {"workspace": str(self.workspace),
                              "model": {"primary": model_ref, "fallbacks": []},
                              "models": {model_ref: {"params": {"maxTokens": 8192}}},
                              "timeoutSeconds": 180}},
                  "models": {"mode": "replace", "providers": {"mimo-benchmark": {
                      "baseUrl": self.relay.url, "api": "anthropic-messages",
                      "apiKey": "${OPENCLAW_BENCH_PROVIDER_TOKEN}",
                      "models": [{"id": "mimo-v2.6-flash", "name": "MiMo v2.6 Flash benchmark",
                                  "reasoning": True, "input": ["text"],
                                  "contextWindow": 1048576, "maxTokens": 8192,
                                  "cost": {"input": .14, "output": .28, "cacheRead": .0028, "cacheWrite": 0}}]}}}}
        (self.state / "openclaw.json").write_text(json.dumps(config, indent=2))
        (self.run_dir / "model.json").write_text(json.dumps(config, indent=2))
        self.metadata = {"driver": "openclaw", "model": model_ref, "wire_model": "mimo-v2.6-flash",
                         "api_format": "anthropic_messages", "base_url": upstream,
                         "version": self._command("--version").strip(),
                         "node_version": subprocess.check_output([self.node, "--version"], text=True).strip(),
                         "entry_sha256": hashlib.sha256(self.entry.read_bytes()).hexdigest(),
                         "package_version": json.loads((self.entry.parent / "package.json").read_text())["version"],
                         "budget_usd": self.budget_usd, "budget_enforcement": "controller_relay_between_calls",
                         "initialization": "native_baseline_setup_and_default_workspace_bootstrap",
                         "initialization_completed": False, "restart_kind": "process_restart",
                         "thinking": "OpenClaw default; effective wire field captured per call",
                         "heartbeat": "native default cadence; short event-driven scenario",
                         "model_config": config}
        lockfile = self.entry.parent.parent.parent / "package-lock.json"
        if lockfile.is_file():
            lock = json.loads(lockfile.read_text())
            self.metadata["npm_integrity"] = lock.get("packages", {}).get("node_modules/openclaw", {}).get("integrity")
            self.metadata["installation_lock_sha256"] = hashlib.sha256(lockfile.read_bytes()).hexdigest()
        self._command("setup", "--baseline", "--workspace", str(self.workspace))
        self._command("config", "validate")
        self._start_gateway()
        self.metadata["initialization_completed"] = True
        return self.metadata

    def _start_gateway(self):
        self.epoch += 1
        self.log_handle = (self.run_dir / f"gateway-{self.epoch}.log").open("w")
        self.process = subprocess.Popen([self.node, str(self.entry), "gateway", "run"],
            cwd=self.temp.name, env=self.env, stdin=subprocess.DEVNULL,
            stdout=self.log_handle, stderr=subprocess.STDOUT, start_new_session=True)
        ready_deadline = min(self.deadline, time.monotonic() + 90)
        while time.monotonic() < ready_deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"OpenClaw Gateway exited before readiness; see gateway-{self.epoch}.log")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/readyz", timeout=1) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(.2)
        raise TimeoutError("OpenClaw Gateway did not become ready")

    def turn(self, message):
        prompt = Path(self.temp.name) / "event.txt"
        prompt.write_text(message)
        envelope = json.loads(self._command("agent", "--session-key", "agent:main:continuity-bench",
                             "--message-file", str(prompt), "--timeout", "180", "--json"))
        return final_reply(envelope)

    def _stop_gateway(self):
        if self.process is None:
            return "already_exited"
        termination = "already_exited"
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            termination = "interrupt"
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=5)
                termination = "forced"
        if self.log_handle:
            self.log_handle.close()
            self.log_handle = None
        log = self.run_dir / f"gateway-{self.epoch}.log"
        if log.exists():
            log.write_text(self._redact(log.read_text(errors="replace")))
        return termination

    def restart(self):
        previous = self.process.pid
        termination = self._stop_gateway()
        exit_code = self.process.returncode
        self._start_gateway()
        return {"restart_verified": previous != self.process.pid and exit_code is not None,
                "previous_pid": previous, "current_pid": self.process.pid,
                "restart_kind": "process_restart", "termination": termination,
                "previous_exit_code": exit_code}

    def telemetry(self):
        # Drain native background work before taking the principal-wide total.
        self._stop_gateway()
        result = self.relay.telemetry()
        records = []
        for source in (self.state / "agents").rglob("openclaw-agent.sqlite"):
            target = self.run_dir / "runtime-traces" / source.relative_to(self.state).with_suffix(".transcripts.jsonl")
            records.extend(export_transcripts(source, target, self.node, self._redact))
        native = transcript_usage(records)
        result["native_usage"] = native
        result["native_usage_matches"] = all(result.get(k) == v for k, v in native.items())
        (self.run_dir / "usage-reconciliation.json").write_text(json.dumps(result, indent=2))
        return result

    def close(self):
        if self.temp is None:
            return
        try:
            self._stop_gateway()
        finally:
            try:
                self.metadata["persona_bootstrap_completed"] = not (self.workspace / "BOOTSTRAP.md").exists()
                # The native database combines transcripts and credentials;
                # export transcript rows only, including compressed records.
                for source in (self.state / "agents").rglob("openclaw-agent.sqlite"):
                    target = self.run_dir / "runtime-traces" / source.relative_to(self.state).with_suffix(".transcripts.jsonl")
                    export_transcripts(source, target, self.node, self._redact)
                for base in (self.state / "agents", self.workspace):
                    for source in base.rglob("*"):
                        if source.is_symlink() or not source.is_file() or source.suffix not in {".jsonl", ".md"}:
                            continue
                        target = self.run_dir / "runtime-traces" / source.relative_to(self.state)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text(self._redact(source.read_text(errors="replace")))
            finally:
                self.relay.close()
                self.temp.cleanup()
