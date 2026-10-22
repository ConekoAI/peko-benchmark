#!/usr/bin/env python3
"""Summarize memory/heartbeat run directories into one JSON evidence file.

  memory_heartbeat_report.py OUT.json RUN_DIR...

Reads only retained artifacts (result.json, provider-calls.jsonl, retained
runtime files); never the vault. Genesis behaviour is tallied across every
principal any listed run created, including failed attempts.
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from continuity_proxy import summarize_calls  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MARKER = "[memory] Daily memory maintenance. The runtime supplies the current brief"


RETRY_MARK = "Your previous answer could not be read."
LINE_RE = re.compile(r"^Line (\d+): ", re.M)


def review_claims(prompt: str) -> int:
    """Claims in an ADR-085 review prompt: `Line N:` headers outside evidence."""
    outside = re.sub(r"<<<.*?>>>", "", prompt, flags=re.S)
    return len(LINE_RE.findall(outside))


def parse_review(answer: str, count: int) -> list[str | None]:
    """Python port of peko-runtime `memory_gate::parse_review` (37777bd6):
    one finding per claim (`supported` / `unsupported`), None if unchecked."""
    checks: list[str | None] = [None] * count
    for raw in answer.splitlines():
        line = raw.strip().lstrip("-* ")
        if line.lower().startswith("line "):
            line = line[5:]
        if line.startswith("<"):
            if ">" not in line:
                continue
            label, rest = line[1:].split(">", 1)
            if label.strip().isdigit():
                slot = int(label.strip()) - 1
            else:
                slot = next((i for i, c in enumerate(checks) if c is None), None)
        else:
            digits = re.match(r"\d*", line).group(0)
            if not digits:
                continue
            slot, rest = int(digits) - 1, line[len(digits):]
        if slot is None or not 0 <= slot < count:
            continue
        rest = rest.lstrip(":.) ").strip().lower()
        if rest.startswith("unsupported"):
            checks[slot] = "unsupported"
        elif rest.startswith("supported"):
            checks[slot] = "supported"
    return checks


def reviewer_answers(calls: list[dict]) -> list[dict]:
    """Each reviewer call: claims, parsed findings, whether it was the
    runtime's retry (#481: format restated; or a cut-off retry at 4x budget)."""
    out = []
    for r in calls:
        if r.get("call_kind") != "memory_review":
            continue
        msgs = (r.get("captured_request") or {}).get("messages") or []
        prompt = "".join(b.get("text", "") for m in msgs if m.get("role") == "user"
                         for b in (m["content"] if isinstance(m["content"], list) else [{"text": m["content"]}]))
        answer = "".join((b.get("text") or "") for b in r.get("captured_response") or [] if b.get("type") == "text")
        count = review_claims(prompt)
        checks = parse_review(answer, count)
        prev = out[-1] if out and out[-1]["principal"] == r.get("principal") else None
        malformed_retry = RETRY_MARK in prompt
        cutoff_retry = bool(prev and prev["claims"] == count and prev["max_tokens"]
                            and (r.get("max_tokens") or 0) >= 4 * prev["max_tokens"])
        out.append({"index": r.get("index"), "principal": r.get("principal"), "phase": r.get("phase"),
                    "claims": count, "max_tokens": r.get("max_tokens"), "stop": r.get("upstream_stop_reason"),
                    "output_tokens": (r.get("usage") or {}).get("output_tokens"),
                    "retry": "malformed" if malformed_retry else "cut_off" if cutoff_retry else None,
                    "supported": checks.count("supported"), "unsupported": checks.count("unsupported"),
                    "unchecked": checks.count(None),
                    "malformed": count > 0 and checks.count(None) > 0,
                    "answer_excerpt": answer[:400]})
    return out


def ledger_rows(principal_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(principal_dir.rglob("ledger/*.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    return rows


def genesis_tally(run_dir: Path, label: str | None = None) -> list[dict]:
    """Per principal created in a run: what its genesis turn did to its jobs,
    hot memory and plans (from the retained ledger, inbox and plans)."""
    out = []
    for pdir in sorted((run_dir / "runtime/data/principals").glob("*")):
        name = pdir.name
        rows = [r for r in ledger_rows(pdir) if (r.get("acting_for") or {}).get("origin", {}).get("job_id") == "genesis"
                and r.get("kind") == "start"]
        cron = [r["params"] for r in rows if r.get("tool") == "Cron"]
        memory_touched = [p for p in cron if p.get("action") in ("update", "delete", "create")
                          and (p.get("id") == "memory" or str(p.get("message", "")).startswith("[memory]")
                               or "memory" in str(p.get("label", "")).lower())]
        inbox = [p for p in glob.glob(str(run_dir / "runtime/principals" / name / "kb/inbox/**/*.proposal.md"),
                                      recursive=True) if '"job_id":"genesis"' in Path(p).read_text()]
        held = sum(Path(p).read_text().count("\n  ```\n") // 2 or Path(p).read_text().count("```") // 2
                   for p in inbox)
        schedule = next(pdir.rglob("cron/schedule.toml"), None)
        jobs = json.loads(schedule.read_text())["jobs"] if schedule else []
        memory_jobs = [j for j in jobs if j["id"] == "memory" or str(j.get("message", "")).startswith("[memory]")]
        out.append({"run": label or run_dir.name, "principal": name,
                    "genesis_tool_calls": len(rows),
                    "memory_job_rewritten_at_genesis": bool(memory_touched),
                    "memory_job_actions": [p.get("action") for p in memory_touched],
                    "memory_job_now": [{"id": j["id"], "runtime_brief": str(j.get("message", "")).startswith(MARKER),
                                        "schedule": j.get("schedule"), "when": j.get("when"),
                                        "enabled": j.get("enabled")} for j in memory_jobs],
                    "genesis_memory_writes_held": len(inbox), "genesis_held_lines": held,
                    "plans_created": sum(1 for r in rows if r.get("tool") == "Plan"
                                         and (r.get("params") or {}).get("action") == "create")})
    return out


def cron_changes(run_dir: Path) -> list[dict]:
    """Cron mutations the principals made themselves, with the result excerpt."""
    out = []
    for pdir in sorted((run_dir / "runtime/data/principals").glob("*")):
        rows = ledger_rows(pdir)
        ends = {r.get("call_id"): r for r in rows if r.get("kind") == "end"}
        for row in rows:
            params = row.get("params") or {}
            if row.get("kind") != "start" or row.get("tool") != "Cron" or params.get("action") in ("list", "history", "show"):
                continue
            end = ends.get(row.get("call_id")) or {}
            out.append({"principal": pdir.name, "at": row.get("ts"),
                        "origin": ((row.get("acting_for") or {}).get("origin") or {}).get("job_id"),
                        "action": params.get("action"), "id": params.get("id"),
                        "fields": sorted(k for k in params if k not in ("action", "id", "message")),
                        "message_prefix": str(params.get("message", ""))[:24] or None,
                        "outcome": end.get("outcome"),
                        "result": ((end.get("result") or {}).get("excerpt") or "")[:240]})
    return out


def leaked_ticks(run_dir: Path) -> list[dict]:
    """Runtime trigger texts found in another principal's trunk transcript."""
    out = []
    names = {p.name for p in (run_dir / "runtime/data/principals").glob("*")}
    displays = {}
    for name in names:
        toml = run_dir / "runtime/principals" / name / "principal.toml"
        if toml.is_file():
            match = re.search(r'display_name\s*=\s*"([^"]+)"', toml.read_text())
            displays[name] = match.group(1) if match else name
    for path in sorted((run_dir / "runtime/data/principals").glob("*/local/sessions/4e103e47*.jsonl")):
        owner = path.parts[-4]
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("role") != "user":
                continue
            for block in row.get("content", []):
                match = re.match(r"\[(keepalive|memory)\][^`]*`([^`]*)`", block.get("text", ""))
                if match and match.group(2) not in (owner, displays.get(owner)):
                    out.append({"trunk_of": owner, "at": row.get("ts"), "trigger": match.group(1),
                                "addressed_to": match.group(2)})
    return out


def heartbeat_digest(run_dir: Path) -> dict:
    result = json.loads((run_dir / "result.json").read_text())
    out = {"run": run_dir.name, "errors": result.get("errors"), "duration_min": result.get("duration_min"),
           "watch_window": result.get("watch_window"), "principals": {}}
    for name, s in (result.get("principals") or {}).items():
        out["principals"][name] = {k: s.get(k) for k in (
            "turns", "quiet_ticks", "fires", "quiet_share", "peer_post_latency_secs", "failure_latency_secs",
            "check_in_at", "check_in_latency_secs", "runs_woken_by", "runs_floor_or_unexplained",
            "per_keepalive_turn", "plans_end", "keepalive_replacements",
            # ADR-086 (round 5): nudges, the fires they brought forward, group chatter.
            "nudges", "nudge_outcomes", "nudge_outcome_counts", "turns_nudged", "turns_nudged_at",
            "quiet_ticks_nudged", "channel_sends")}
        out["principals"][name]["run_starts"] = [r.get("started") for r in s.get("runs", [])]
        out["principals"][name]["quiet_at"] = [q.get("at") for q in s.get("quiet", [])]
        out["principals"][name]["failure_probe_status"] = [r.get("status") for r in s.get("failure_probe_runs", [])]
        out["principals"][name]["usage"] = {k: {f: v.get(f) for f in ("request_count", "input_tokens",
                                                                       "cache_read_tokens", "output_tokens", "cost_usd")}
                                            for k, v in (s.get("usage") or {}).items()}
        out["principals"][name]["run_reasons"] = [r.get("reasons") for r in s.get("runs", [])]
    out["genesis_plans"] = result.get("genesis_plans")
    out["schedule_changes_by_principal"] = cron_changes(run_dir)
    out["usage_total"] = (result.get("usage") or {}).get("total")
    return out


def memory_digest(rep_dir: Path) -> dict:
    from memory_heartbeat_memory import regrade
    result = regrade(rep_dir)
    calls = [json.loads(line) for line in (rep_dir / "provider-calls.jsonl").read_text().splitlines() if line.strip()]
    reviews = [{"phase": r.get("phase"), "max_tokens": r.get("max_tokens"), "usage": r.get("usage"),
                "stop": r.get("upstream_stop_reason"),
                "response_block_types": [b.get("type") for b in r.get("captured_response") or []],
                "response_text": "".join((b.get("text") or "") for b in r.get("captured_response") or []
                                         if b.get("type") == "text")[:600] or None}
               for r in calls if r.get("call_kind") == "memory_review"]
    nights = []
    for night in result.get("nights", []):
        row = {"night": night["night"], "d9_hold": night.get("d9_hold"), "memory_job": night.get("memory_job"),
               "principals": {}}
        for name, p in night["principals"].items():
            grade = p.get("grade") or {}
            row["principals"][name] = {
                "memory_run": p.get("memory_run"), "files_written": p.get("files_written"),
                "hot_added": p.get("hot_added"), "hot_removed": p.get("hot_removed"),
                "held": [{"reason": h["reason"], "line": h["line"], "file": h.get("file")} for h in p.get("held", [])],
                "grade": {k: v for k, v in grade.items() if k not in ("items",)},
                "item_outcomes": {k: {"kind": v["kind"], "landed": bool(v["landed"]), "held": bool(v["held"]),
                                      "other_kb_files": v["other_kb_files"]}
                                  for k, v in (grade.get("items") or {}).items()},
                "stale_left_in_memory": p.get("stale_left_in_memory"),
                "owner_facts_in_hot": p.get("owner_facts_in_hot"), "owner_facts_lost": p.get("owner_facts_lost"),
                "memory_entries_truncated": p.get("memory_entries_truncated"),
                "physical_lines": p.get("physical_lines"),
                "memory_bytes": p.get("memory_bytes"), "conventions_bytes": p.get("conventions_bytes"),
                "dream_files": p.get("dream_files"), "journal_files": p.get("journal_files"),
                "plants": p.get("plants"),
                "day": {"plants": (p.get("day") or {}).get("plants"),
                        "hot_added": (p.get("day") or {}).get("hot_added"),
                        "held": [{"reason": h["reason"], "line": h["line"]} for h in (p.get("day") or {}).get("held", [])]}}
        raw = next((n for n in json.loads((rep_dir / "result.json").read_text()).get("nights", [])
                    if n["night"] == night["night"]), {})
        row["adversary_channel"] = [
            {"author": e.get("author") or e.get("sender") or e.get("from"), "text": e.get("text") or e.get("body")}
            for e in (raw.get("adversary_channel") or []) if isinstance(e, dict)]
        nights.append(row)
    by_phase = {k: {f: v.get(f) for f in ("request_count", "input_tokens", "output_tokens", "cost_usd")}
                for k, v in ((result.get("usage") or {}).get("by_phase") or {}).items()}
    return {"run": f"{rep_dir.parent.name}/{rep_dir.name}", "errors": result.get("errors"),
            "memory_review_overrides": result.get("memory_review_overrides", {}),
            "genesis_plans": result.get("genesis_plans"),
            "memory_job_after_genesis": result.get("memory_job_after_genesis"),
            "nights": nights, "reviewer_calls": reviews, "reviewer_answers": reviewer_answers(calls),
            "reviewer_usage": summarize_calls([r for r in calls if r.get("call_kind") == "memory_review"]),
            "usage_by_phase": by_phase, "usage_total": (result.get("usage") or {}).get("total")}


def all_spend(runs: list[Path]) -> dict:
    """Relay usage over every listed run, failed attempts included."""
    totals = {"requests": 0, "incomplete": 0, "uncached_input": 0, "cache_read": 0, "output": 0}
    for path in (p for run in runs for p in run.rglob("provider-calls.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if not row.get("forwarded"):
                continue
            usage = row.get("usage", {})
            totals["requests"] += 1
            totals["incomplete"] += not (row.get("completed") and row.get("status") == 200)
            totals["uncached_input"] += usage.get("input_tokens", 0)
            totals["cache_read"] += usage.get("cache_read_input_tokens", 0)
            totals["output"] += usage.get("output_tokens", 0)
    totals["reference_cost_usd"] = round((totals["uncached_input"] * .14 + totals["output"] * .28
                                          + totals["cache_read"] * .0028) / 1e6, 4)
    return totals


def main(argv: list[str]) -> int:
    out_path, runs = Path(argv[0]), [Path(a) for a in argv[1:]]
    evidence = {"evidence_kind": "real_llm_memory_heartbeat_evaluation", "heartbeat": [], "memory": [],
                "genesis": [], "cross_principal_trunk_deliveries": [], "runs": [r.name for r in runs]}
    for run in runs:
        if run.name.endswith("-memory-review-probe"):
            probe = json.loads((run / "result.json").read_text())
            evidence["reviewer_probe"] = {"run": run.name, "model": probe.get("model"),
                                          "peko_budget": probe.get("peko_budget"), "rows": probe.get("rows")}
            continue
        if run.name.endswith("-memory-plant-probe"):
            probe = json.loads((run / "result.json").read_text())
            usage = [r.get("usage") or {} for r in probe["rows"]]
            evidence["reviewer_plant_probe"] = {
                "run": run.name, "model": probe.get("model"), "runtime": probe.get("runtime"),
                "claims": probe.get("claims"), "rows": probe.get("rows"),
                "reference_cost_usd": round(sum(u.get("input_tokens", 0) * .14 + u.get("output_tokens", 0) * .28
                                                + u.get("cache_read_input_tokens", 0) * .0028 for u in usage) / 1e6, 5)}
            continue
        reps = sorted(run.glob("rep*")) or [run]
        for rep in reps:
            if not (rep / "runtime").is_dir():
                continue
            evidence["genesis"].extend(genesis_tally(rep, rep.name if rep == run else f"{run.name}/{rep.name}"))
            if rep.name.startswith("rep") or "attention" in rep.name:
                evidence.setdefault("schedule_changes", []).extend(
                    {"run": rep.name if rep == run else f"{run.name}/{rep.name}", **x} for x in cron_changes(rep))
            evidence["cross_principal_trunk_deliveries"].extend(
                {"run": rep.name if rep == run else f"{run.name}/{rep.name}", **x} for x in leaked_ticks(rep))
            if not (rep / "result.json").is_file():
                continue
            result = json.loads((rep / "result.json").read_text())
            if result.get("evidence_kind") == "real_llm_heartbeat_pilot" and result.get("principals"):
                evidence["heartbeat"].append(heartbeat_digest(rep))
            elif "nights" in result and result["nights"]:
                evidence["memory"].append(memory_digest(rep))
    evidence["spend_all_attempts"] = all_spend(runs)
    evidence["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted(ROOT.glob("runner/memory_*.py")) + sorted(ROOT.glob("scenarios/memory_heartbeat/*.toml"))}
    out_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    print(json.dumps({"heartbeat_runs": len(evidence["heartbeat"]), "memory_reps": len(evidence["memory"]),
                      "genesis_principals": len(evidence["genesis"]),
                      "cross_principal_trunk_deliveries": len(evidence["cross_principal_trunk_deliveries"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
