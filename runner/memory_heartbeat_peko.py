"""Isolated multi-principal Peko daemon for the memory/heartbeat evaluation.

One passphrase vault, one daemon, several principals, one accounting relay.
Each relay record is labelled (principal, call kind, triggering job) from the
payload; no prompt text is persisted. The controller may stop the daemon and
edit a principal's persisted schedule (declared in the run metadata) to fire
the nightly memory job on demand instead of waiting for a real quiet night.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import time
from pathlib import Path

from continuity_peko import PekoDriver
from continuity_proxy import AnthropicRelay, summarize_calls

# ADR-085 reviewer and ADR-078 policy-judge system prompts begin with these.
REVIEW_SYSTEM_PREFIX = "You check lines a personal agent wants to add to its long-term memory"
TRIGGERS = (("[keepalive]", "keepalive"), ("[memory]", "memory"), ("[genesis]", "genesis"))


RUNTIME_CONTEXT = "<runtime-context>"
ORIGIN_RE = re.compile(r"Origin: cron job ([A-Za-z0-9_\-:]+)")


def _blocks(content) -> list[dict]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [b for b in content or [] if isinstance(b, dict)]


def _text(value) -> str:
    return "\n".join(b.get("text", "") for b in _blocks(value) if b.get("type") == "text")


def trigger_text(payload: dict) -> str:
    """The newest user text that is neither a tool result nor runtime context:
    the message that began this turn (an owner post, a cron fire, an agent task)."""
    for message in reversed(payload.get("messages", [])):
        if message.get("role") != "user":
            continue
        for block in reversed(_blocks(message.get("content"))):
            text = block.get("text", "") if block.get("type") == "text" else ""
            # Async completion notes ("📨 [Helper: …]") are not what began a turn.
            if (text.strip() and not text.lstrip().startswith(RUNTIME_CONTEXT)
                    and not text.lstrip().startswith("\U0001f4e8")):
                return text
    return ""


def identity_text(payload: dict) -> str:
    """The newest principal-identity context block (it names the principal and the
    run's origin; the runtime re-injects it only when it changes)."""
    for message in reversed(payload.get("messages", [])):
        for block in reversed(_blocks(message.get("content"))):
            text = block.get("text", "") if block.get("type") == "text" else ""
            if text.lstrip().startswith(RUNTIME_CONTEXT) and "## Principal identity" in text:
                return text
    return ""


def classify(payload: dict, names: dict[str, str]) -> dict:
    """Labels for one provider request. `names` maps display name -> principal.

    The principal is the one named in the runtime identity block. Reviewer
    calls carry no identity; they are labelled by their fixed system prompt.
    The job is read from the runtime's own trigger prefixes; other text is a
    conversation turn (or a spawned agent's task). No prompt text is kept.
    """
    system = _text(payload.get("system"))
    if system.startswith(REVIEW_SYSTEM_PREFIX):
        return {"call_kind": "memory_review", "principal": None, "job": "memory_review"}
    identity = identity_text(payload)
    principal = next((p for name, p in names.items()
                      if name in identity or f"(`{p}`)" in identity), None)
    if principal is None:
        # Fallback: the workspace path its tools and context mention most.
        blob = json.dumps(payload.get("messages", []))
        counts = {p: blob.count(f"/principals/{p}/") for p in names.values()}
        best = max(counts, key=counts.get, default=None)
        principal = best if best and counts[best] else None
    trigger = trigger_text(payload).lstrip()
    # The identity block states the run's origin, e.g. "Origin: cron job keepalive".
    origin = ORIGIN_RE.search(identity)
    if origin:
        job = origin.group(1) if origin.group(1) in ("keepalive", "memory", "genesis") else "cron:other"
    else:
        job = next((label for prefix, label in TRIGGERS if trigger.startswith(prefix)), None)
    if job is None:
        job = "conversation" if trigger else "unknown"
    return {"call_kind": "turn" if payload.get("tools") else "toolless",
            "principal": principal, "job": job,
            "trigger_digest": hashlib.sha256(trigger.encode()).hexdigest()[:12] if trigger else None}


def usage_by(records: list[dict], *keys: str) -> dict:
    """Relay usage grouped by label keys, e.g. ("principal", "job")."""
    groups: dict[str, list] = {}
    for record in records:
        label = "/".join(str(record.get(k)) for k in keys)
        groups.setdefault(label, []).append(record)
    return {label: summarize_calls(rows) for label, rows in sorted(groups.items())}


class MultiPeko(PekoDriver):
    def __init__(self, run_dir: Path, timeout_secs: int, budget_usd: float, limits: dict):
        super().__init__(run_dir, timeout_secs, budget_usd)
        self.limits = limits
        self.relay = None
        self.names: dict[str, str] = {}
        self.principals: list[str] = []
        self.controller_edits: list[dict] = []
        self.phase_label = "setup"

    # -- setup ---------------------------------------------------------------
    def start(self) -> dict:
        key = os.environ.get("PEKO_API_KEY") or os.environ.get("MIMO_API_KEY")
        if not key:
            raise ValueError("PEKO_API_KEY or MIMO_API_KEY is required")
        upstream = self.base_url
        self.relay = AnthropicRelay(upstream, key, self.run_dir / "provider-calls.jsonl",
                                    time.monotonic() + self.timeout_secs, self.budget_usd,
                                    self.limits, lambda: self.phase_label)
        self.relay.classify = lambda payload: classify(payload, self.names)
        # Reviewer calls quote fictional scenario lines; keep their text to diagnose findings.
        self.relay.capture_kinds = {"memory_review"}
        # peko-runtime #479 asks the reviewer for 2048 + 64 x claims tokens and
        # retries a cut-off answer at 4x; do not let the relay's cap refuse it.
        self.relay.max_tokens_caps = {"memory_review": 65536}
        self.base_url = self.relay.url
        self.config_env = {k: v for k, v in self.config_env.items() if k in (
            "PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR", "TMPDIR", "PEKO_BIN")
            or k.startswith("PEKO_MODEL_") or k.startswith("PEKO_CACHE_READ_")
            or k in ("PEKO_CONTEXT_WINDOW", "PEKO_COST_BASIS", "PEKO_API_FORMAT", "PEKO_MAX_OUTPUT_TOKENS")}
        self.config_env["PEKO_API_KEY"] = self.relay.token
        binary = self.config_env.get("PEKO_BIN")
        if not binary or not Path(binary).is_file():
            raise ValueError("PEKO_BIN must name an existing peko CLI binary")
        self.binary = Path(binary).resolve()
        self.daemon = self.binary.with_name("peko-daemon")
        if not self.daemon.is_file():
            raise ValueError("build peko-daemon beside PEKO_BIN before benchmarking")
        import tempfile
        self.deadline = time.monotonic() + self.timeout_secs
        self.temp = tempfile.TemporaryDirectory(prefix="pbm-", dir="/tmp")
        home = Path(self.temp.name)
        peko_home = home / ".peko"
        (peko_home / "run").mkdir(parents=True)
        self.env = dict(self.config_env)
        self.env.update(HOME=str(home), USERPROFILE=str(home), PEKO_HOME=str(peko_home),
                        PEKO_CONFIG_DIR=str(peko_home), PEKO_DATA_DIR=str(peko_home / "data"),
                        PEKO_CACHE_DIR=str(peko_home / "cache"),
                        PEKO_DAEMON_SOCK=str(peko_home / "run/daemon.sock"), PEKO_DAEMON_PIPE="",
                        PEKO_MASTER_PASSPHRASE="memory-heartbeat-bench-vault-passphrase",
                        PEKO_IDENTITY_PASSPHRASE="memory-heartbeat-bench-vault-passphrase",
                        PEKO_UNLOCK_METHOD="passphrase")
        self.env.pop("PEKO_TEST_RESOLVER_BOOTSTRAP", None)
        # Quiet-tick decisions ("attention fire runs: ...") are debug lines.
        self.env["RUST_LOG"] = "info,peko_core::daemon::cron_engine=debug"
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
        rates = [pricing.get(k) for k in ("input_per_million", "output_per_million")]
        if any(not isinstance(x, (float, int)) or isinstance(x, bool)
               or not math.isfinite(x) or x < 0 for x in rates):
            raise ValueError("model needs both finite nonnegative pricing rates for a budgeted run")
        self.metadata = {"driver": "peko-multi", "model": self.model, "wire_model": model.get("modelId"),
                         "api_format": self.api_format, "base_url": upstream, "pricing_hint": pricing,
                         "cost_basis": self.env.get("PEKO_COST_BASIS", "runtime_pricing_hint"),
                         "version": self._command("version").strip(), "budget_usd": self.budget_usd,
                         "relay_limits": self.limits,
                         "cli_sha256": hashlib.sha256(self.binary.read_bytes()).hexdigest(),
                         "daemon_sha256": hashlib.sha256(self.daemon.read_bytes()).hexdigest(),
                         "principals": {}, "controller_edits": self.controller_edits}
        return self.metadata

    def create(self, name: str, display: str, description: str, goals: list[str],
               budget_usd: float = 1.0, extra: str = "", genesis_timeout: float = 900) -> dict:
        """Native genesis with the seeded keepalive and memory jobs."""
        seed = Path(self.temp.name) / f"seed-{name}.toml"
        seed.write_text(f"name = {json.dumps(name)}\npreferred_model_id = {json.dumps(self.model)}\n"
                        f"[identity]\ndisplay_name = {json.dumps(display)}\n"
                        f"description = {json.dumps(description)}\n"
                        f"[intent]\ngoals = {json.dumps(goals)}\n"
                        f"[quota]\nbudget_per_cycle = {budget_usd}\n"
                        "request_count = 400\ninput_tokens = 20000000\noutput_tokens = 400000\n" + extra)
        self.names[display] = name
        started = time.time()
        # Detach and wait on the persisted run row: genesis turns on MiMo can
        # exceed the CLI's 300 s wait (observed up to ~6 min with 16 requests).
        self._command("create", name, "--seed", str(seed), "--detach")
        self._ready()
        deadline = time.time() + genesis_timeout
        while True:
            try:
                runs = json.loads(self.schedule_path(name).read_text()).get("runs", [])
            except (ValueError, json.JSONDecodeError):
                runs = []
            done = [r for r in runs if r.get("job_id") == "genesis" and r.get("finished_at")]
            if done:
                if done[-1].get("status") != "success":
                    raise RuntimeError(f"genesis of {name} ended {done[-1].get('status')}")
                break
            if time.time() > deadline:
                raise TimeoutError(f"genesis of {name} did not finish in {genesis_timeout}s")
            time.sleep(5)
        self.principals.append(name)
        info = {"display": display, "goals": goals, "genesis_secs": round(time.time() - started, 1)}
        self.metadata["principals"][name] = info
        return info

    # -- paths and persisted state --------------------------------------------
    @property
    def home(self) -> Path:
        return Path(self.temp.name) / ".peko"

    def workspace(self, name: str) -> Path:
        return self.home / "principals" / name

    def data_root(self, name: str) -> Path:
        return self.home / "data/principals" / name

    def schedule_path(self, name: str) -> Path:
        paths = list(self.data_root(name).rglob("cron/schedule.toml"))
        if len(paths) != 1:
            raise ValueError(f"no unique native schedule for {name}")
        return paths[0]

    def jobs(self, name: str) -> dict[str, dict]:
        return {j["id"]: j for j in json.loads(self.schedule_path(name).read_text()).get("jobs", [])}

    def edit_jobs(self, name: str, reason: str, edit) -> None:
        self.edit_many({name: edit}, reason)

    def edit_many(self, edits: dict, reason: str) -> None:
        """Stop the daemon, apply `edit(jobs_list)` per principal, restart once.
        Every edit is recorded in the run metadata as a controller edit."""
        self._stop_owned_daemon()
        try:
            self._apply_edits(edits, reason)
        finally:
            # Never leave the daemon down after a failed edit.
            self._command("daemon", "start", "--interval", "5")
            self._ready()

    def _apply_edits(self, edits: dict, reason: str) -> None:
        for name, edit in edits.items():
            path = self.schedule_path(name)
            schedule = json.loads(path.read_text())
            before = json.dumps(schedule["jobs"], sort_keys=True)
            edit(schedule["jobs"])
            path.write_text(json.dumps(schedule, indent=2))
            self.controller_edits.append({"at": time.time(), "principal": name, "reason": reason,
                                          "changed": before != json.dumps(schedule["jobs"], sort_keys=True)})

    # -- traffic ---------------------------------------------------------------
    def send(self, name: str, message: str) -> dict:
        """Owner DM turn; returns the persisted final reply with timing."""
        started = time.time()
        prompt = Path(self.temp.name) / "event.txt"
        prompt.write_text(message)
        timed_out = False
        # A DM turn can outlive the CLI's wait; it keeps running in the daemon,
        # and the next send is refused until it ends. Wait it out (round 4).
        for _ in range(60):
            try:
                self._command("send", name, "--file", str(prompt), "--wait")
                break
            except TimeoutError:
                timed_out = True
                break
            except RuntimeError:
                last = self.run_dir / f"command-{self.command_index:02}.log"
                if "active run in flight" not in last.read_text():
                    raise
                time.sleep(15)
        else:
            raise RuntimeError(f"{name}: session stayed busy for 15 minutes")
        if timed_out:
            return {"text": None, "timed_out": True, "secs": round(time.time() - started, 1)}
        log = json.loads(self._command("log", name, "--limit", "1", "--json"))
        reply = (log.get("messages") or [{}])[0]
        return {"text": reply.get("text"), "id": reply.get("id"),
                "secs": round(time.time() - started, 1)}

    def group(self, channel: str, creator: str, title: str, members: list[str]) -> None:
        self._command("channel", "create", creator, title, "--id", channel, "--json")
        for member in members:
            self._command("channel", "invite", channel, creator, member, "--json")

    def post(self, channel: str, sender: str, text: str) -> dict:
        """Post as a member principal (no model call) or `me` (the owner)."""
        if sender == "me":
            out = self._command("send", channel, text)
            return {"raw": out.strip()[:200], "at": time.time()}
        return {"event": json.loads(self._command("channel", "post", channel, sender, text, "--json")),
                "at": time.time()}

    def peek(self, channel: str) -> list:
        snapshot = json.loads(self._command("channel", "peek", channel, "--json"))
        return snapshot if isinstance(snapshot, list) else snapshot.get("events", [])

    # -- telemetry and retention ------------------------------------------------
    def records(self) -> list[dict]:
        with self.relay.lock:
            return [dict(r) for r in self.relay.records]

    def telemetry(self) -> dict:
        self.metadata["telemetry_drain_completed"] = self.relay.drain()
        rows = self.records()
        return {"total": summarize_calls(rows),
                "by_principal_job": usage_by(rows, "principal", "job"),
                "by_phase": usage_by(rows, "phase"),
                "by_kind": usage_by(rows, "call_kind")}

    def retain(self) -> None:
        """Copy kb, plans, schedules, run history, audit and transcripts; never vaults or keys."""
        root = self.home
        for base in (root / "principals", root / "data", root / "logs"):
            if not base.exists():
                continue
            for source in base.rglob("*"):
                if not source.is_file() or source.is_symlink():
                    continue
                if any(part in ("keys", "vault", "credentials", "identity", "identities") for part in source.parts):
                    continue
                if source.suffix not in {".md", ".json", ".jsonl", ".toml", ".log"}:
                    continue
                if source.stat().st_size > 20_000_000:
                    continue
                target = self.run_dir / "runtime" / source.relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(self._redact(source.read_text(errors="replace")))

    def close(self):
        if self.temp:
            try:
                self._stop_owned_daemon()
            finally:
                try:
                    self.retain()
                finally:
                    try:
                        super().close()
                    finally:
                        if self.relay:
                            self.relay.close()


def utc(ts: float | None = None) -> str:
    return dt.datetime.fromtimestamp(ts or time.time(), dt.timezone.utc).isoformat()
