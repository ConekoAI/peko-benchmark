"""Responsibility adapters using native Peko cron and OpenClaw heartbeat."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from continuity_openclaw import OpenClawDriver, final_reply
from continuity_peko import PekoDriver
from continuity_proxy import AnthropicRelay
from continuity_usage import reconcile_usage
from responsibility_prepared import prepare_peko, prepare_claw, arm_peko, set_claw_due_times
from prompt_profile import PromptProfiler
from responsibility_topology import (claw_setup, peko_setup, supervisor_prompt,
                                     verify_claw, verify_peko, task_paths,
                                     handoff_prompt, direct_action_prompt, SEPARATED_CONTRACT_VERSION)

POLICY = {"max_tokens": 4096, "thinking": {"type": "disabled"},
          "request_limit": 60, "output_limit": 30000,
          "probe_allowance": {"request_limit": 8, "output_limit": 6000, "budget_usd": .01}}
API_CONTRACT_VERSION = 3


def action_contract(url):
    """Static simulator interface, without obligation facts or grading feedback."""
    return (f"Isolated simulator: GET {url}/world for current dependency state; "
            f"POST {url}/actions with JSON using native Bash/exec curl (Content-Type: application/json). "
            "Only HTTP POST actions count as deliveries. No real messaging, browser, or external network. "
            'Release: {"kind":"send_release","project":"...","revision":"...","recipient":"...","delivery_key":"..."}. '
            'Blocked input: {"kind":"request_input","project":"...","reason":"dependency_blocked"}. '
            "A response receipt means recorded, not approved: wrong/repeated attempts are still graded. ")


def state_contract():
    """Shared state-maintenance instructions; no controller-derived statuses."""
    return ("Maintain one canonical durable commitment table and an append-only receipt log shared by all conversations. "
            "Hot memory may point to that table; avoid divergent copies of current statuses. "
            "After each action record its exact payload, elapsed time and HTTP receipt, then update the canonical "
            "commitment state before ending the turn. Mark a release delivered only when a recorded send_release "
            "matches the documented schema, accepted revision/recipient/key, and matching ready build observed "
            "during the active watch. A recording receipt alone does not certify a correct action. "
            "Without a matching release receipt, retain pending; cancellation stays cancelled. "
            "A request_input receipt leaves the release blocked, not delivered or unblocked. "
            "Before reporting memory, reconcile the canonical table with accepted requirements and actual receipts: "
            "a stale pending table cell must not override a later matching release receipt. "
            "Do not invent receipts or repeat deliveries to repair memory. ")


def monitor_prompt(url, cadence):
    return ("Internal supervision. " + action_contract(url) + state_contract()
            + "Read durable responsibility notes. "
            "Continue accepted commitments only when watch_active is true. Inspect requirements before acting. "
            "Use POST /actions for meaningful deliveries or required input, persist receipts, and prevent repeats. "
            f"No extra polling, timers, background shell loops, or delegated monitors: cadence is {cadence:g}s. "
            "Make at most one GET in this turn. When inactive or nothing needs action, END THIS TURN quietly. "
            "Do not wait for readiness inside the turn; tool yieldMs does not set a polling cadence. "
            "Never notify about routine checks.")


def task_monitor_prompt(url, cadence):
    return ("You are the dedicated release-watch task worker, not the organizational supervisor. "
            + task_paths() + monitor_prompt(url, cadence)
            + " Maintain only canonical task receipts and current state. Leave routine hot-memory, journal, "
            "skill, and session-tree maintenance to the supervisor; do not rewrite those on every check. "
            + direct_action_prompt(url))


class PekoResponsibility(PekoDriver):
    def __init__(self, run_dir, timeout_secs, budget_usd, simulator, mode):
        super().__init__(run_dir, timeout_secs, budget_usd)
        self.sim, self.mode, self.relay = simulator, mode, None
        self.principal = "responsibility-bench"
        self.topology = self.sim.spec.get("topology", "flattened")
        self.topology_checks = []
        self.formation = self.sim.spec.get("formation", "model")

    def start(self):
        key = os.environ.get("PEKO_API_KEY") or os.environ.get("MIMO_API_KEY")
        if not key:
            raise ValueError("PEKO_API_KEY or MIMO_API_KEY is required")
        upstream = self.base_url
        self.relay = AnthropicRelay(upstream, key, self.run_dir / "provider-calls.jsonl",
                                   time.monotonic() + self.timeout_secs, self.budget_usd,
                                   POLICY, self.phase)
        if self.sim.spec.get("profile_prompt"):
            self.relay.profiler = PromptProfiler()
        self.base_url = self.relay.url
        self.config_env = {k: v for k, v in self.config_env.items() if k in (
            "PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR", "TMPDIR", "PEKO_BIN")
            or k.startswith("PEKO_MODEL_") or k.startswith("PEKO_CACHE_READ_")
            or k in ("PEKO_CONTEXT_WINDOW", "PEKO_COST_BASIS", "PEKO_API_FORMAT")}
        self.config_env.update(PEKO_API_KEY=self.relay.token, PEKO_MAX_OUTPUT_TOKENS="4096")
        cadence = self.sim.spec["cadence_secs"]
        rhythm = (f"Replace the default keepalive: CronDelete id=keepalive, then CronCreate "
                  f"label=responsibility-monitor interval_ms={int(cadence * 1000)} message="
                  + monitor_prompt(self.sim.url, cadence)) if self.mode == "supervisory" else (
                  "For this controlled ablation, disable the default keepalive with CronUpdate id=keepalive enabled=false. "
                  "Do not create any scheduled or background work; only react to external messages.")
        goal = ("You are Responsibility Bench, a concise release coordinator for an isolated simulation. "
                "On genesis keep the existing memory structure, avoid speculative files or delegation, "
                "record this purpose in hot memory and configure the requested native cadence. " + rhythm)
        if self.topology == "separated":
            goal = ("Responsibility Bench is a persistent principal coordinating simulated release obligations. "
                    "Its trunk is the organizational supervisor; /release-watch owns periodic task execution; "
                    "peer owner/review conversations receive requirement changes. Each session follows its current "
                    "turn's role, not every other role. Keep existing memory scaffolding and authoritative shared "
                    "requirements/receipts without inventing facts. " + handoff_prompt()
                    + peko_setup(self.sim.url, cadence, task_monitor_prompt(self.sim.url, cadence)))
        if self.formation == "prepared":
            goal = ("Responsibility Bench coordinates simulated releases. " + handoff_prompt()
                    + "In genesis keep native identity and memory scaffolding, disable the default keepalive; "
                    "do not create task sessions or schedules. The benchmark controller prepares an empty "
                    "organization afterward. Owner messages will supply requirements. End genesis promptly.")
        self.native_budget_usd = self.budget_usd + POLICY["probe_allowance"]["budget_usd"]
        self.seed_extra = ("\n[identity]\ndisplay_name = \"Responsibility Bench\"\n"
                           "description = \"Concise coordinator for simulated release obligations\"\n"
                           "\n[intent]\ngoals = [" + json.dumps(goal) + "]\n")
        try:
            super().start()
            if self.formation == "prepared":
                prepare_peko(self, task_monitor_prompt(self.sim.url, cadence))
        finally:
            self.metadata.update(base_url=upstream, common_wire_policy=POLICY, continuation_mode=self.mode,
                                 cadence_secs=cadence, initialization="defined_purpose_native_genesis",
                                 api_contract_version=SEPARATED_CONTRACT_VERSION if self.topology == "separated" else API_CONTRACT_VERSION,
                                 topology=self.topology)
        return self.metadata

    def validate_topology(self, stage):
        root = Path(self.temp.name) / ".peko/data/principals" / self.principal
        schedule_files = list(root.rglob("cron/schedule.toml"))
        session_files = list(root.rglob("sessions.json"))
        if len(schedule_files) != 1 or len(session_files) != 1:
            raise ValueError("no unique native schedule and session index for topology verification")
        schedule = json.loads(schedule_files[0].read_text())
        sessions = json.loads(session_files[0].read_text())
        check = verify_peko(schedule, sessions, self.sim.spec["cadence_secs"]) | {"stage": stage}
        self.topology_checks.append(check)
        (self.run_dir / f"topology-{stage}.json").write_text(self._redact(json.dumps(
            {"check": check, "schedule": schedule, "sessions": sessions}, indent=2)))
        self.metadata["topology_checks"] = self.topology_checks
        if not check["verified"]:
            raise ValueError("separated topology registration failed: " + "; ".join(check["errors"]))
        return check

    def begin_watch(self):
        if self.formation == "prepared":
            arm_peko(self)

    def phase(self):
        return phase_for(self.sim)

    def conversation(self, message, review=False):
        if not review:
            return self.turn(message)
        # A separate group conversation under the same principal. The owner
        # forwards tentative analyst proposals here; this is not an auth test.
        self._command("channel", "create", self.principal, "Review conversation",
                      "--id", "group:bench-review", "--json")
        self._command("channel", "invite", "group:bench-review", self.principal, "user:local", "--json")
        self._command("send", "group:bench-review", message)
        until = min(self.deadline, time.monotonic() + 90)
        while time.monotonic() < until:
            snapshot = json.loads(self._command("channel", "peek", "group:bench-review", "--json"))
            # Store-level group events preserve the native conversation evidence.
            events = snapshot if isinstance(snapshot, list) else snapshot.get("events", [])
            for event in reversed(events):
                sender = event.get("sender", event.get("author", {}))
                if ((event.get("kind") == "posted" and isinstance(sender, str)
                     and (sender.startswith("principal:") or sender.startswith("prin_")))
                    or (isinstance(sender, dict) and sender.get("kind") == "principal")):
                    return json.dumps(event)
            time.sleep(1)
        raise TimeoutError("no principal reply in native review group")

    def telemetry(self):
        self.metadata["telemetry_drain_completed"] = self.relay.drain()
        self._stop_owned_daemon()
        root = Path(self.temp.name) / ".peko/data/principals" / self.principal
        states = list(root.rglob("quota_state.json"))
        if len(states) != 1:
            raise ValueError("no unique persisted principal quota state")
        state = json.loads(states[0].read_text())
        native = reconcile_usage(root, state, self.metadata["pricing_hint"], .0028)
        result = self.relay.telemetry()
        result["native_usage"] = native
        result["native_usage_matches"] = all(result.get(k) == native.get(k) for k in (
            "request_count", "uncached_input_tokens", "cache_read_tokens", "cache_creation_tokens", "output_tokens"))
        return result

    def close(self):
        # Preserve native memory and schedules as well as transcripts, never vaults.
        if self.temp:
            root = Path(self.temp.name) / ".peko"
            for base in (root / "principals", root / "data/principals", root / "data/workspaces"):
                if base.exists():
                    for source in base.rglob("*"):
                        if (source.is_file() and not source.is_symlink()
                            and (source.suffix == ".md" or
                                 (source.suffix in {".json", ".toml"} and "cron" in source.parts))):
                            target = self.run_dir / "runtime-traces" / source.relative_to(root)
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_text(self._redact(source.read_text(errors="replace")))
        try:
            super().close()
        finally:
            if self.relay:
                self.relay.close()


class ClawResponsibility(OpenClawDriver):
    def __init__(self, run_dir, timeout_secs, budget_usd, simulator, mode):
        super().__init__(run_dir, timeout_secs, budget_usd)
        self.sim, self.mode = simulator, mode
        self.topology = self.sim.spec.get("topology", "flattened")
        self.topology_checks = []
        self.formation = self.sim.spec.get("formation", "model")

    def configure(self, config):
        cadence = self.sim.spec["cadence_secs"]
        config["agents"]["defaults"].update(thinkingDefault="off", heartbeat={
            "every": f"{cadence * (2 if self.topology == 'separated' else 1):g}s" if self.mode == "supervisory" and self.formation != "prepared" else "0m",
            "session": "agent:main:responsibility", "target": "none",
            "prompt": supervisor_prompt(cadence) if self.topology == "separated" else monitor_prompt(self.sim.url, cadence),
            "timeoutSeconds": 90})
        config["tools"] = {"exec": {"host": "gateway", "security": "full", "ask": "off"}}
        for model in config["agents"]["defaults"]["models"].values():
            model["params"]["maxTokens"] = 4096
        self.relay.policy = POLICY
        self.relay.phase = lambda: phase_for(self.sim)
        if self.sim.spec.get("profile_prompt"):
            self.relay.profiler = PromptProfiler()

    def start(self):
        try:
            metadata = super().start()
        finally:
            self.metadata.update(common_wire_policy=POLICY, continuation_mode=self.mode,
                                 cadence_secs=self.sim.spec["cadence_secs"],
                                 api_contract_version=SEPARATED_CONTRACT_VERSION if self.topology == "separated" else API_CONTRACT_VERSION,
                                 topology=self.topology)
        if self.formation == "prepared":
            prepare_claw(self, task_monitor_prompt(self.sim.url, self.sim.spec["cadence_secs"]))
            metadata.update(persona_bootstrap_completed=True, initialization="controller_prepared_empty_native_topology")
            return metadata
        instruction = ("Onboarding: your agreed name is Responsibility Bench. Your agreed vibe is concise release "
                  "coordinator for an isolated simulation, emoji 📋. Skip avatar generation and optional apps/plugins. "
                  "Complete applicable BOOTSTRAP steps now in one bounded turn: persist identity, soul and user "
                  "(the user is the benchmark owner); set native identity with the configured CLI. "
                  f"CLI entry: {self.node} {self.entry}. Workspace: {self.workspace}. "
                  "No recommendations or questions are needed. Remove BOOTSTRAP.md when done. "
                  "Reply briefly.")
        if self.topology == "separated":
            instruction += (" Set identity directly with "
                            f"{self.node} {self.entry} agents set-identity --agent main "
                            f"--workspace {self.workspace} --name 'Responsibility Bench' "
                            "--theme 'Concise release coordinator for an isolated simulation' --emoji '📋'. "
                            "No identity CLI discovery is needed. ")
        instruction += (claw_setup(self.node, self.entry, self.sim.spec["cadence_secs"],
                                   task_monitor_prompt(self.sim.url, self.sim.spec["cadence_secs"]))
                        if self.topology == "separated" else
                        "Do not start any tasks or schedules beyond the configured heartbeat.")
        try:
            self.turn(instruction)
        finally:
            metadata["persona_bootstrap_completed"] = not (self.workspace / "BOOTSTRAP.md").exists()
        completed = not (self.workspace / "BOOTSTRAP.md").exists()
        metadata.update(initialization="native_baseline_and_completed_llm_onboarding",
                        persona_bootstrap_completed=completed, common_wire_policy=POLICY,
                        continuation_mode=self.mode, cadence_secs=self.sim.spec["cadence_secs"],
                        heartbeat="native configured cadence, owner task session, internal-only output",
                        api_contract_version=SEPARATED_CONTRACT_VERSION if self.topology == "separated" else API_CONTRACT_VERSION,
                        topology=self.topology)
        if not completed:
            raise RuntimeError("OpenClaw persona onboarding did not finish before task clock")
        return metadata

    def begin_watch(self):
        if self.formation == "prepared":
            set_claw_due_times(self, armed=True)

    def validate_topology(self, stage):
        schedule = json.loads(self._command("automations", "list", "--all", "--json"))
        sessions = json.loads(self._command("sessions", "--all-agents", "--json"))
        check = verify_claw(schedule, sessions, self.sim.spec["cadence_secs"],
                            require_supervisor=not (self.formation == "prepared" and stage == "post-setup")) | {"stage": stage}
        self.topology_checks.append(check)
        (self.run_dir / f"topology-{stage}.json").write_text(self._redact(json.dumps(
            {"check": check, "schedule": schedule, "sessions": sessions}, indent=2)))
        self.metadata["topology_checks"] = self.topology_checks
        if not check["verified"]:
            raise ValueError("separated topology registration failed: " + "; ".join(check["errors"]))
        return check

    def turn(self, message):
        return self.conversation(message)

    def conversation(self, message, review=False):
        prompt = Path(self.temp.name) / "event.txt"
        prompt.write_text(message)
        key = "agent:main:review" if review else "agent:main:responsibility"
        return final_reply(json.loads(self._command("agent", "--session-key", key,
                          "--message-file", str(prompt), "--thinking", "off", "--timeout",
                          "180" if self.topology == "separated" else "90", "--json")))

    def telemetry(self):
        schedules = json.loads(self._command("automations", "list", "--all", "--json"))
        (self.run_dir / "native-schedules.json").write_text(self._redact(json.dumps(schedules, indent=2)))
        self.metadata["telemetry_drain_completed"] = self.relay.drain()
        return super().telemetry()


def phase_for(sim):
    if sim.phase != "watch":
        return sim.phase
    t = sim.elapsed()
    return "watch_idle" if any(a <= t < b for a, b in sim.spec["idle_windows"]) else "watch_active"
