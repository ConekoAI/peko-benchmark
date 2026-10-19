#!/usr/bin/env python3
"""Aggregate retained prepared-execution reports into one comparison JSON.

Usage: responsibility_rerun_report.py OUT.json REPORT_DIR...

Reads only retained controller ledgers, call records and result files; it
never re-grades or repairs a run. Missing usage stays null.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEEP = ("passed", "completed_obligations", "on_time_obligations", "missed_deadlines",
        "delivery_latency_secs", "forbidden_actions", "repeated_actions", "premature_deliveries",
        "stale_deliveries", "cancelled_deliveries", "quiet_window_actions", "remained_quiet",
        "unnecessary_notifications", "memory_facts_correct", "memory_facts_total",
        "memory_measurement", "requested_human_input", "human_interventions",
        "controller_continuations", "native_outbound_attempts", "watch_status_reads",
        "restart_verified", "topology_registered", "policy_diagnostics_passed")
USAGE = ("request_count", "rejected_request_count", "uncached_input_tokens", "cache_read_tokens",
         "output_tokens", "cost_usd", "usage_complete")


def escalation(ledger, spec):
    """Every request_input attempt for the blocked obligation, with its timing class."""
    blocked = next(o for o in spec["obligations"] if o.get("status") == "blocked")
    rows = []
    for row in ledger:
        action = row.get("action") or {}
        if row.get("kind") == "action" and action.get("kind") == "request_input":
            t = row["elapsed_secs"]
            rows.append({"elapsed_secs": t, "phase": row.get("phase"), "project": action.get("project"),
                         "timing": ("after_watch" if row.get("phase") != "watch" else
                                    "premature" if t < blocked["blocked_at"] else
                                    "late" if t > blocked["deadline"] else "in_window")})
    return {"blocked_at": blocked["blocked_at"], "deadline": blocked["deadline"], "attempts": rows,
            "first_valid_elapsed_secs": next((r["elapsed_secs"] for r in rows if r["timing"] == "in_window"), None)}


def actions(ledger):
    return [{"elapsed_secs": r["elapsed_secs"], "phase": r.get("phase"), "kind": r["action"].get("kind"),
             "project": r["action"].get("project")} for r in ledger
            if r.get("kind") == "action" and r.get("action", {}).get("kind") != "memory"]


def run(path):
    result = json.loads((path / "result.json").read_text())
    spec = json.loads((path / "scenario.json").read_text())
    ledger = [json.loads(line) for line in (path / "ledger.jsonl").read_text().splitlines() if line.strip()] \
        if (path / "ledger.jsonl").exists() else []
    metrics, usage = result.get("metrics", {}), result.get("usage", {})
    native = usage.get("native_usage") or {}
    reads = [r["elapsed_secs"] for r in ledger if r.get("kind") == "read" and r.get("phase") == "watch"]
    gaps = [round(b - a, 3) for a, b in zip(reads, reads[1:])]
    return {"report_id": path.name, "driver": result["metadata"].get("driver") or path.name.rsplit("-", 1)[-1],
            "errors": result.get("errors", []), "wall_secs": result.get("wall_secs"),
            "metrics": {k: metrics.get(k) for k in KEEP},
            "observed_precondition_violations": (metrics.get("observed_preconditions") or {}).get("violations"),
            "missing_receipts": (metrics.get("receipt_retention") or {}).get("missing_receipts"),
            "topology_execution_verified": (metrics.get("topology_execution") or {}).get("verified"),
            "watch_reads_elapsed_secs": reads, "max_read_gap_secs": max(gaps) if gaps else None,
            "actions": actions(ledger), "escalation": escalation(ledger, spec),
            "usage": {k: usage.get(k) for k in USAGE} | {
                "native_cost_usd": native.get("cost_usd"), "native_request_count": native.get("request_count"),
                "native_usage_matches": usage.get("native_usage_matches")},
            "phase_usage": {p: {k: v.get(k) for k in ("request_count", "output_tokens", "cost_usd", "usage_complete")}
                            for p, v in (result.get("phase_usage") or {}).items()}}


def main():
    out, paths = Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]
    runs = [run(p if p.is_absolute() else ROOT / p) for p in paths]
    out.write_text(json.dumps({"evidence_kind": "prepared_execution_rerun", "runs": runs}, indent=2) + "\n")
    for r in runs:
        m = r["metrics"]
        print(r["report_id"], "pass" if m["passed"] else "fail", f"on_time={m['on_time_obligations']}",
              f"repeat={m['repeated_actions']}", f"mem={m['memory_facts_correct']}/{m['memory_facts_total']}",
              f"esc={r['escalation']['first_valid_elapsed_secs']}", f"cost={r['usage']['cost_usd']}",
              f"errors={len(r['errors'])}")


if __name__ == "__main__":
    main()
