#!/usr/bin/env python3
"""Run a multi-turn continuity scenario (Python 3.11+, no packages)."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import time
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    raise SystemExit("Python 3.11+ required; try python3.12 runner/continuity.py")

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = """Simulated release environment. Your final reply must be exactly one JSON object:
{"actions": []} when no delivery is due, or {"actions": [{"kind": "send_release",
"project": "...", "revision": "...", "recipient": "...", "delivery_key": "..."}]}.
Each listed action is a delivery request to the simulator, not a report about work.
The runner executes and records every listed action, including repeats. Deliver
only once per commitment, after its build-green event. Use no real messaging
tools. You may use your persistent workspace to remember commitments. Do not
schedule background deliveries: this scenario evaluates event-driven continuity.
"""
FIELDS = {"kind", "project", "revision", "recipient", "delivery_key"}


def load_scenario(path: Path, seed: int) -> dict:
    spec = tomllib.loads(path.read_text())
    nonce = f"{random.Random(seed).getrandbits(48):012x}"
    variables = {k: v.format(nonce=nonce) for k, v in spec["variables"].items()}
    steps = []
    for original in spec["steps"]:
        step = dict(original)
        if step.get("kind") != "restart":
            step["message"] = CONTRACT + "\nEvent:\n" + step["message"].format(**variables)
            step["expected_actions"] = [
                {k: v.format(**variables) for k, v in action.items()}
                for action in step["expected_actions"]
            ]
        steps.append(step)
    return {**spec, "variables": variables, "steps": steps, "seed": seed}


def parse_actions(reply: str) -> list[dict]:
    # Permit a single fenced JSON object, never search prose for a lucky match.
    text = reply.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4].strip()
    payload = json.loads(text)
    if not isinstance(payload, dict) or set(payload) != {"actions"}:
        raise ValueError("reply must be an object with exactly the actions key")
    actions = payload["actions"]
    if not isinstance(actions, list):
        raise ValueError("actions must be an array")
    for action in actions:
        if (not isinstance(action, dict) or set(action) != FIELDS
                or action.get("kind") != "send_release"
                or any(not isinstance(v, str) or not v.strip() for v in action.values())):
            raise ValueError("invalid send_release action")
    return actions


def score_scenario(spec: dict, observations: list[dict]) -> dict:
    """Score only observed replies; an empty/incomplete trace cannot pass."""
    turns = [s for s in spec["steps"] if s.get("kind") != "restart"]
    expected_ids = [s["id"] for s in spec["steps"]]
    trace_complete = [o.get("step_id") for o in observations] == expected_ids
    by_id = {o.get("step_id"): o for o in observations}
    restart_verified = all(
        by_id.get(s["id"], {}).get("restart_verified") is True
        for s in spec["steps"] if s.get("kind") == "restart"
    )
    correct = 0
    forbidden = 0
    cancelled = 0
    duplicates = 0
    stale = 0
    premature = 0
    protocol_errors = 0
    seen = set()
    deliveries = []
    eligible = next(s for s in turns if s["expected_actions"])
    target = eligible["expected_actions"][0]
    revised = False
    for step in turns:
        if step["id"] == "revise-and-cancel":
            revised = True
        observation = by_id.get(step["id"], {})
        try:
            actions = parse_actions(observation.get("reply", ""))
        except (ValueError, TypeError):
            actions = []
            protocol_errors += 1
            continue
        correct += actions == step["expected_actions"]
        remaining = list(step["expected_actions"])
        for action in actions:
            deliveries.append((step["id"], action))
            if action in remaining:
                remaining.remove(action)
            else:
                forbidden += 1
            signature = (action["project"], action["revision"], action["recipient"])
            duplicates += signature in seen
            seen.add(signature)
            premature += step["id"] in {"accept", "distract", "revise-and-cancel"}
            cancelled += revised and action["project"] == spec["variables"]["cancelled_project"]
            if revised and action["project"] == target["project"]:
                stale += (action["revision"] != target["revision"]
                          or action["recipient"] != target["recipient"])
    successful = any(step_id == eligible["id"] and action == target
                     for step_id, action in deliveries)
    # This is conditional response latency, not autonomous notification latency.
    latency = by_id.get(eligible["id"], {}).get("wall_secs") if successful else None
    passed = trace_complete and restart_verified and correct == len(turns) and protocol_errors == 0
    return {
        "passed": passed,
        "obligation_completion_rate": float(successful),
        "correct_turn_rate": correct / len(turns),
        "forbidden_action_count": forbidden,
        "cancelled_action_count": cancelled,
        "duplicate_delivery_count": duplicates,
        "stale_delivery_count": stale,
        "premature_delivery_count": premature,
        "protocol_error_count": protocol_errors,
        "trace_complete": trace_complete,
        "restart_verified": restart_verified,
        "recovery_success": successful and restart_verified,
        "response_latency_secs": latency,
    }


class ValidationDriver:
    """Oracle/empty traces validate graders; they are never model evidence."""
    def __init__(self, spec: dict, oracle: bool):
        self.spec = spec
        self.oracle = oracle
        self.index = 0

    def start(self):
        return {"driver": "oracle" if self.oracle else "empty", "model": None}

    def turn(self, message: str):
        while self.spec["steps"][self.index].get("kind") == "restart":
            self.index += 1
        step = self.spec["steps"][self.index]
        self.index += 1
        return json.dumps({"actions": step["expected_actions"] if self.oracle else []})

    def restart(self):
        return {"restart_verified": True, "simulation": True}

    def telemetry(self):
        return {"cost_usd": None, "input_tokens": None, "output_tokens": None,
                "request_count": None}

    def close(self):
        pass


def execute(spec: dict, driver, run_dir: Path, evidence_kind: str) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    # This file contains future events/answers. Never pass it to the agent.
    (run_dir / "scenario.json").write_text(json.dumps(spec, indent=2))
    observations = []
    errors = []
    metadata = {}
    telemetry = {"cost_usd": None, "input_tokens": None, "output_tokens": None,
                 "request_count": None}
    started = time.monotonic()
    try:
        metadata = driver.start()
        with (run_dir / "observations.jsonl").open("w") as trace:
            for step in spec["steps"]:
                t0 = time.monotonic()
                record = {"step_id": step["id"]}
                if step.get("kind") == "restart":
                    record.update(driver.restart())
                else:
                    record.update(message=step["message"], reply=driver.turn(step["message"]))
                record["wall_secs"] = round(time.monotonic() - t0, 3)
                observations.append(record)
                trace.write(json.dumps(record) + "\n")
                trace.flush()
    except Exception as exc:
        errors.append(str(exc))
    finally:
        # Failed model runs still consumed resources; preserve partial counters.
        metadata = metadata or getattr(driver, "metadata", {})
        if metadata:
            try:
                telemetry = driver.telemetry()
            except Exception as exc:
                errors.append(f"telemetry: {exc}")
        try:
            driver.close()
        except Exception as exc:
            errors.append(f"cleanup: {exc}")
    metrics = score_scenario(spec, observations)
    metrics["passed"] = metrics["passed"] and not errors
    completed = metrics["obligation_completion_rate"]
    cost = telemetry.get("cost_usd")
    metrics["cost_usd_per_completed_obligation"] = cost / completed if cost is not None and completed else None
    result = {"schema_version": 1, "scenario": spec["id"], "seed": spec["seed"],
              "evidence_kind": evidence_kind, "driver": metadata, "metrics": metrics,
              "telemetry": telemetry, "wall_secs": round(time.monotonic() - started, 3),
              "errors": errors}
    (run_dir / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", default="changed-commitment")
    ap.add_argument("--driver", choices=["oracle", "empty", "peko"], required=True)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget-usd", type=float, help="required for live Peko; per-repetition quota")
    args = ap.parse_args()
    if args.reps < 1 or args.seed < 0:
        ap.error("reps must be positive and seed nonnegative")
    if args.driver == "peko" and (args.budget_usd is None or not 0 < args.budget_usd < float("inf")):
        ap.error("live Peko requires a finite positive --budget-usd")
    path = ROOT / "scenarios" / "continuity" / f"{args.scenario}.toml"
    if not path.is_file() or path.parent != ROOT / "scenarios" / "continuity":
        ap.error("unknown scenario")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report = ROOT / "reports" / f"{stamp}-continuity-{args.driver}"
    results = []
    for rep in range(args.reps):
        spec = load_scenario(path, args.seed + rep)
        run_dir = report / f"run{rep + 1}"
        if args.driver == "peko":
            from continuity_peko import PekoDriver
            driver = PekoDriver(run_dir, spec["timeout_secs"], args.budget_usd)
            kind = "model_run"
        else:
            driver = ValidationDriver(spec, args.driver == "oracle")
            kind = "grader_self_test"
        result = execute(spec, driver, run_dir, kind)
        results.append(result)
        print(json.dumps({"rep": rep + 1, "evidence_kind": kind, **result["metrics"]}))
    summary = {"evidence_kind": kind, "runs": len(results),
               "passes": sum(r["metrics"]["passed"] for r in results), "results": results}
    (report / "summary.json").write_text(json.dumps(summary, indent=2))
    lines = [f"# Continuity: {args.scenario}", "", f"Evidence: `{kind}`", "",
             "| rep | pass | obligations | forbidden | stale | cancelled | duplicates | estimated USD |",
             "|---|---|---|---|---|---|---|---|"]
    for i, result in enumerate(results, 1):
        m = result["metrics"]
        cost = result["telemetry"].get("cost_usd")
        lines.append(f"| {i} | {m['passed']} | {m['obligation_completion_rate']:.0%} | "
                     f"{m['forbidden_action_count']} | {m['stale_delivery_count']} | "
                     f"{m['cancelled_action_count']} | {m['duplicate_delivery_count']} | "
                     f"{cost if cost is not None else 'unavailable'} |")
    lines += ["", "Oracle/empty runs validate scoring and are not agent capability results.",
              "This scenario measures event-driven continuity, not unattended autonomy.", ""]
    (report / "summary.md").write_text("\n".join(lines))
    print(f"Report: {report}")
    return 0 if all(r["metrics"]["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
