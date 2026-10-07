"""Controller-owned world and append-only evidence for native background agents.

Only present dependency state is exposed. Actions are recorded, including wrong
ones, without grading feedback. Future changes and expected obligations are not
available through the HTTP API. This is cooperative isolation, not a sandbox.
"""
from __future__ import annotations

import json
import random
import threading
import time
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def load_spec(path: Path, seed: int, scale: float = 1) -> dict:
    if scale < 1:
        raise ValueError("scale must be >= 1; native supervision has a 60s floor")
    spec = tomllib.loads(path.read_text())
    nonce = f"{random.Random(seed).getrandbits(48):012x}"
    spec["seed"], spec["scale"], spec["nonce"] = seed, scale, nonce
    for name in ("duration_secs", "cadence_secs", "restart_at"):
        spec[name] *= scale
    spec["idle_windows"] = [[a * scale, b * scale] for a, b in spec["idle_windows"]]
    for row in spec["changes"] + spec["obligations"]:
        row["project"] += "-" + nonce
        if "recipient" in row:
            row["recipient"] += "-" + nonce
            row["delivery_key"] += "-" + nonce
        for key in ("at", "ready_at", "blocked_at", "deadline"):
            if key in row:
                row[key] *= scale
    return spec


class Simulator:
    def __init__(self, spec: dict, run_dir: Path, clock=time.monotonic):
        self.spec, self.run_dir, self.clock = spec, run_dir, clock
        self.origin = None
        self.phase = "setup"
        self.rows = []
        self.lock = threading.RLock()
        self.world = {o["project"]: {"ready": False, "revision": o["revision"]}
                      for o in spec["obligations"]}
        self.applied = 0
        self.server = None
        self.thread = None

    def elapsed(self):
        return round(self.clock() - self.origin, 3) if self.origin is not None else None

    def record(self, kind, **fields):
        with self.lock:
            row = {"seq": len(self.rows) + 1, "kind": kind, "phase": self.phase,
                   "elapsed_secs": self.elapsed(), "wall_time": time.time(), **fields}
            self.rows.append(row)
            with (self.run_dir / "ledger.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            return row

    def begin(self):
        self.origin = self.clock()
        self.phase = "watch"
        self.record("watch_started")

    def advance(self):
        with self.lock:
            if self.origin is None:
                return
            for change in self.spec["changes"][self.applied:]:
                if change["at"] > self.elapsed():
                    break
                self.world[change["project"]] = {k: change[k] for k in ("ready", "revision")}
                self.applied += 1
                # Actual observed application time, not the ideal scheduled time.
                self.record("world_change", scheduled_at=change["at"], change=change)

    def observe(self):
        with self.lock:
            self.advance()
            state = {"watch_active": self.phase == "watch", "elapsed_secs": self.elapsed(),
                     "duration_secs": self.spec["duration_secs"], "world_version": self.applied,
                     "dependencies": json.loads(json.dumps(self.world))}
            self.record("read", world_version=self.applied, snapshot=state)
            return state

    def submit(self, action):
        with self.lock:
            self.advance()
            row = self.record("action", action=action)
            # No oracle feedback or deduplication; repeated attempts remain visible.
            return {"recorded": True, "receipt": row["seq"]}

    def start_server(self):
        simulator = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, code, body):
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path != "/world":
                    return self.reply(404, {"error": "unknown resource"})
                self.reply(200, simulator.observe())

            def do_POST(self):
                if self.path != "/actions":
                    return self.reply(404, {"error": "unknown resource"})
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 16384:
                        raise ValueError("invalid body size")
                    action = json.loads(self.rfile.read(size))
                    if not isinstance(action, dict):
                        raise ValueError("action must be an object")
                except (ValueError, TypeError) as exc:
                    simulator.record("protocol_error", error=str(exc))
                    return self.reply(400, {"error": str(exc)})
                self.reply(200, simulator.submit(action))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        return self.url

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=2)


def cadence_coverage(spec: dict, rows: list[dict]) -> dict:
    """Post-hoc observation coverage, never exposed through the world API.

    A read is an opportunity only when it observes the required dependency
    state in the obligation's time window. It does not prove the agent used
    that read or could finish an action within the remaining slack.
    """
    required = {o["project"]: o for o in spec["obligations"] if not o.get("cancelled")}
    world = {o["project"]: {"ready": False, "revision": o["revision"]}
             for o in spec["obligations"]}
    opportunities = {project: [] for project in required}
    reads = []
    for row in rows:
        if row["kind"] == "world_change":
            change = row["change"]
            world[change["project"]] = {k: change[k] for k in ("ready", "revision")}
        if row["kind"] != "read" or row["phase"] != "watch" or row["elapsed_secs"] is None:
            continue
        t = row["elapsed_secs"]
        reads.append(t)
        for project, obligation in required.items():
            state = world[project]
            eligible = (not state["ready"] and obligation["blocked_at"] <= t
                        if "blocked_at" in obligation else
                        state["ready"] and state["revision"] == obligation["revision"])
            if eligible and t <= obligation["deadline"]:
                opportunities[project].append(t)
    complete = any(r["kind"] == "watch_finished" for r in rows)
    horizon = max((r["elapsed_secs"] for r in rows
                   if r["phase"] == "watch" and r["elapsed_secs"] is not None), default=0)
    boundaries = [0, *reads, horizon]
    gaps = [round(b - a, 3) for a, b in zip(reads, reads[1:])]
    return {"version": 1, "watch_complete": complete, "observation_horizon_secs": horizon,
            "nominal_cadence_secs": spec["cadence_secs"],
            "first_read_elapsed_secs": reads[0] if reads else None,
            "first_read_offset_mod_cadence_secs": round(reads[0] % spec["cadence_secs"], 3) if reads else None,
            "inter_read_gaps_secs": gaps, "max_inter_read_gap_secs": max(gaps, default=None),
            "max_unobserved_gap_secs": max((round(b - a, 3) for a, b in zip(boundaries, boundaries[1:])), default=0),
            "obligations_observed_in_time": sum(bool(ts) for ts in opportunities.values()),
            "obligations_without_timely_observation": [p for p, ts in opportunities.items() if not ts],
            "obligations": {p: {"eligible_read_times_secs": ts, "eligible_read_count": len(ts),
                "max_remaining_secs": round(required[p]["deadline"] - ts[0], 3) if ts else None,
                "min_remaining_secs": round(required[p]["deadline"] - ts[-1], 3) if ts else None}
                for p, ts in opportunities.items()}}


def score(spec: dict, rows: list[dict], restart: dict, finished: bool) -> dict:
    expected = {o["project"]: o for o in spec["obligations"]}
    completed, on_time, latencies = set(), set(), {}
    forbidden = stale = cancelled = premature = duplicate = chatter = protocol = 0
    help_requests = 0
    seen = set()
    memory = None
    memory_reports = 0
    idle_actions = 0
    changes = {}
    for row in rows:
        if row["kind"] == "world_change" and row["change"]["ready"]:
            changes.setdefault(row["change"]["project"], row["elapsed_secs"])
    for row in rows:
        if row["kind"] == "protocol_error":
            protocol += 1
        if row["kind"] != "action":
            continue
        action = row["action"]
        t = row["elapsed_secs"]
        kind = action.get("kind")
        if kind == "memory" and row["phase"] == "probe":
            memory = action.get("facts")
            memory_reports += 1
            continue
        idle_actions += row["phase"] == "watch" and any(a <= t < b for a, b in spec["idle_windows"])
        project = action.get("project")
        obligation = expected.get(project) if isinstance(project, str) else None
        signature = json.dumps(action, sort_keys=True)
        duplicate += signature in seen
        seen.add(signature)
        valid = False
        if obligation and kind == "send_release":
            cancelled += bool(obligation.get("cancelled"))
            stale += any(action.get(k) != obligation[k] for k in ("revision", "recipient", "delivery_key"))
            eligible = changes.get(obligation["project"])
            premature += eligible is None or t is None or t < eligible
            valid = (set(action) == {"kind", "project", "revision", "recipient", "delivery_key"}
                     and not obligation.get("cancelled") and "ready_at" in obligation
                     and eligible is not None and t is not None and t >= eligible
                     and row["phase"] == "watch"
                     and all(action.get(k) == obligation[k] for k in ("revision", "recipient", "delivery_key")))
            if valid:
                if obligation["project"] in completed:
                    valid = False
                else:
                    completed.add(obligation["project"])
                    latencies[obligation["project"]] = round(t - eligible, 3)
                    if t <= obligation["deadline"]:
                        on_time.add(obligation["project"])
        elif obligation and kind == "request_input":
            help_requests += 1
            valid = (set(action) == {"kind", "project", "reason"}
                     and action.get("reason") == "dependency_blocked"
                     and "blocked_at" in obligation and t is not None
                     and obligation["blocked_at"] <= t <= obligation["deadline"]
                     and row["phase"] == "watch" and obligation["project"] not in completed)
            if valid:
                completed.add(obligation["project"])
                on_time.add(obligation["project"])
        else:
            chatter += 1
        forbidden += not valid
    required = {o["project"] for o in spec["obligations"] if not o.get("cancelled")}
    policy_keys = ("deadline", "blocked_at") if spec.get("measure_memory_policy") else ()
    facts_total = len(expected) * (4 + len(policy_keys))
    facts_correct = 0
    memory_valid = memory_reports == 1 and isinstance(memory, list) and all(
        isinstance(f, dict) and isinstance(f.get("project"), str) for f in memory)
    if memory_valid:
        memory_valid = len(memory) == len(expected) and len({f.get("project") for f in memory}) == len(expected)
    if memory_valid:
        by_project = {f.get("project"): f for f in memory}
        for name, obligation in expected.items():
            fact = by_project.get(name, {})
            actual_status = ("cancelled" if obligation.get("cancelled") else
                             "blocked" if "blocked_at" in obligation else
                             "delivered" if name in completed else "pending")
            facts_correct += sum(fact.get(k) == obligation[k]
                                 for k in ("revision", "recipient", "delivery_key"))
            facts_correct += fact.get("status") == actual_status
            facts_correct += sum(k in fact and fact[k] == obligation.get(k) for k in policy_keys)
    restarts = [r for r in rows if r["kind"] == "restart"]
    protocol += not memory_valid
    reads = [r for r in rows if r["kind"] == "read" and r["phase"] == "watch"]
    return {"passed": bool(finished and restart.get("restart_verified") and required == on_time
                           and not forbidden and not protocol and facts_correct == facts_total),
            "trace_complete": finished, "restart_verified": restart.get("restart_verified", False),
            "required_obligations": len(required), "completed_obligations": len(completed & required),
            "obligation_completion_rate": len(completed & required) / len(required),
            "on_time_obligations": len(on_time & required), "missed_deadlines": len(required - on_time),
            "delivery_latency_secs": latencies, "forbidden_actions": forbidden,
            "stale_deliveries": stale, "cancelled_deliveries": cancelled,
            "premature_deliveries": premature, "repeated_actions": duplicate,
            "unnecessary_notifications": chatter, "quiet_window_actions": idle_actions,
            "remained_quiet": idle_actions == 0 and chatter == 0,
            "memory_facts_correct": facts_correct, "memory_facts_total": facts_total,
            "memory_accuracy": facts_correct / facts_total, "protocol_errors": protocol,
            "memory_measurement": ("measured" if memory_valid else "invalid" if memory_reports else "unmeasured"),
            "requested_human_input": help_requests,
            "human_interventions": sum(r["kind"] == "intervention" for r in rows),
            "watch_status_reads": len(reads),
            "unchanged_state_reads": sum(a["world_version"] == b["world_version"] for a, b in zip(reads, reads[1:])),
            "restart_count": len(restarts), "cadence_coverage": cadence_coverage(spec, rows)}
