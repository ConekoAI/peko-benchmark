#!/usr/bin/env python3
"""Runtime evidence for a retained Peko responsibility report (read-only).

Usage: responsibility_runtime_evidence.py REPORT_DIR...

Prints one JSON object per report with:
- review: the acting-for stamps (actor, trust) of tool calls in the review
  group's compartment, from the hash-chained ledger and `tool.call` audit
  events, plus `policy.review` decisions;
- cron: every native `cron.result` status, and job enabled /
  consecutive_failures in each topology snapshot (auto-disable included);
- seeded_job_edits: Cron delete / update-enabled calls on the seeded genesis,
  keepalive and memory jobs, their results and the model's next tool call.
"""
import json
import sys
from collections import Counter
from pathlib import Path

SEEDED = {"genesis", "keepalive", "memory"}
REVIEW_CHANNEL = "group:bench-review"


def rows(paths):
    for path in paths:
        for line in path.read_text().splitlines():
            if line.strip():
                yield json.loads(line)


def review_stamps(traces):
    ledger = [r for r in rows(sorted(traces.rglob("ledger/*.jsonl"))) if r.get("kind") == "start"]
    audit = list(rows(sorted(traces.rglob("audit/*.jsonl"))))
    def in_review(stamp):
        compartment = (stamp or {}).get("compartment") or {}
        return compartment.get("channel") == REVIEW_CHANNEL or (stamp or {}).get("actor") == REVIEW_CHANNEL
    ledger_review = [r["acting_for"] for r in ledger if in_review(r.get("acting_for"))]
    audit_review = [(r.get("details") or {}).get("acting_for") for r in audit
                    if r.get("event_type") == "tool.call" and in_review((r.get("details") or {}).get("acting_for"))]
    reviews = [{"decision": (r["details"].get("decision") or "").split(":")[0], "tool": r["details"].get("tool_name"),
                "actor": (r["details"].get("acting_for") or {}).get("actor"),
                "trust": (r["details"].get("acting_for") or {}).get("trust")}
               for r in audit if r.get("event_type") == "policy.review"]
    stamps = Counter((s.get("actor"), s.get("trust")) for s in ledger_review + audit_review if s)
    return {"ledger_calls": len(ledger_review), "audit_calls": len(audit_review),
            "stamps": [{"actor": a, "trust": t, "count": n} for (a, t), n in stamps.items()],
            "policy_reviews": reviews,
            "floor_denials": sum(r.get("event_type") == "tool.floor_denied" for r in audit)}


def cron(run, traces):
    audit = list(rows(sorted(traces.rglob("audit/*.jsonl"))))
    results = [r["details"] for r in audit if r.get("event_type") == "cron.result"]
    statuses = Counter((d.get("job_name"), d.get("status")) for d in results)
    snapshots = {}
    for stage in ("post-setup", "pre-watch", "post-restart", "post-watch"):
        path = run / f"topology-{stage}.json"
        if path.exists():
            schedule = json.loads(path.read_text())["schedule"]
            snapshots[stage] = [{"id": j["id"], "enabled": j.get("enabled"),
                                 "consecutive_failures": j.get("consecutive_failures")} for j in schedule["jobs"]]
    disabled = sorted({j["id"] for jobs in snapshots.values() for j in jobs if j["enabled"] is False})
    return {"results": [{"job": j, "status": s, "count": n} for (j, s), n in sorted(statuses.items())],
            "skipped_or_interrupted": [d for d in results if d.get("status") in ("skipped", "interrupted")],
            "catch_ups": sum(bool(d.get("catch_up")) for d in results),
            "jobs_by_stage": snapshots, "disabled_jobs": disabled}


def seeded_edits(traces):
    edits = []
    for path in sorted(traces.rglob("sessions/*.jsonl")):
        events = list(rows([path]))
        calls = [(i, b) for i, e in enumerate(events) for b in (e.get("content") or [])
                 if isinstance(b, dict) and b.get("type") == "tool_call"]
        results = {b.get("tool_call_id"): b for e in events for b in (e.get("content") or [])
                   if isinstance(b, dict) and b.get("type") == "tool_result"}
        for n, (i, call) in enumerate(calls):
            args = call.get("arguments") or {}
            target = args.get("id") or args.get("label")
            if call.get("name") != "Cron" or target not in SEEDED:
                continue
            if not (args.get("action") == "delete" or (args.get("action") == "update" and args.get("enabled") is False)):
                continue
            result = results.get(call.get("id"), {})
            text = json.dumps(result.get("content"))[:300]
            following = [{"tool": c.get("name"), "arguments": json.dumps(c.get("arguments"))[:200]}
                         for _, c in calls[n + 1:n + 3]]
            edits.append({"session": path.stem, "ts": events[i].get("ts"), "arguments": args,
                          "is_error": bool(result.get("is_error")), "result": text, "next_calls": following})
    return edits


def main():
    for arg in sys.argv[1:]:
        run = Path(arg)
        traces = run / "runtime-traces"
        print(json.dumps({"report_id": run.name, "review": review_stamps(traces), "cron": cron(run, traces),
                          "seeded_job_edits": seeded_edits(traces)}))


if __name__ == "__main__":
    main()
