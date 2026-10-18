#!/usr/bin/env python3
"""Live evaluation of Peko's attention heartbeat (ADR-083/084) and nightly
memory pass with its source and reviewer gates (ADR-080 rev 2/3, ADR-085).

  memory_heartbeat.py heartbeat [--minutes N]   # real wall clock, default cadence
  memory_heartbeat.py memory    [--reps N]      # scripted day(s), forced memory pass

Everything runs in an isolated HOME with a passphrase vault; provider calls go
through the accounting relay. The analysis helpers below are pure and tested
offline (tests/test_memory_heartbeat.py).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import threading
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_heartbeat_peko import MultiPeko, utc  # noqa: E402
from continuity_proxy import summarize_calls  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ROOT / "scenarios/memory_heartbeat"


def parse_ts(value: str | None) -> float | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------- analysis --
def job_runs(schedule: dict, job_id: str) -> list[dict]:
    """Run rows (turns) of one job, oldest first, with epoch times."""
    rows = [r for r in schedule.get("runs", []) if r.get("job_id") == job_id]
    out = [{"started": parse_ts(r.get("started_at")), "finished": parse_ts(r.get("finished_at")),
            "status": r.get("status"), "error": (r.get("error") or "")[:300]} for r in rows]
    return sorted(out, key=lambda r: r["started"] or 0)


def quiet_events(audit_rows: list[dict], principal_id: str, job_id: str) -> list[dict]:
    """`cron.quiet` audit events of one job (ADR-083 D3 / ADR-080 D9)."""
    out = []
    for row in audit_rows:
        if row.get("event_type") != "cron.quiet":
            continue
        details = row.get("details") or {}
        if details.get("job_id") != job_id or row.get("agent_did") != principal_id:
            continue
        out.append({"at": parse_ts(row.get("timestamp")), "scheduled_at": details.get("scheduled_at"),
                    "next_run_at": details.get("next_run_at"), "waiting_for": details.get("waiting_for")})
    return out


def fire_reasons(log_lines: list[str]) -> list[dict]:
    """Debug lines explaining why an attention fire ran (timestamp, reasons)."""
    out = []
    for line in log_lines:
        if "attention fire runs:" not in line:
            continue
        try:
            ts = parse_ts(line.split()[0])
        except ValueError:
            ts = None
        reasons = re.sub(r"\s+job=\S+\s*$", "", line.split("attention fire runs:", 1)[1]).strip()
        out.append({"at": ts, "reasons": [r.strip() for r in reasons.split(";") if r.strip()]})
    return out


def attribute_reasons(runs: list[dict], reasons: list[dict], window: float = 3.0) -> None:
    """Attach the debug reasons logged just before a run started (in place)."""
    for run in runs:
        match = [r for r in reasons if r["at"] is not None and run["started"] is not None
                 and 0 <= run["started"] - r["at"] <= window]
        run["reasons"] = match[-1]["reasons"] if match else None


def first_run_after(runs: list[dict], ts: float) -> dict | None:
    return next((r for r in runs if r["started"] and r["started"] >= ts), None)


def latency(events: list[float], runs: list[dict]) -> list[float | None]:
    """Seconds from each event to the next turn start (None: no turn after it)."""
    out = []
    for at in events:
        run = first_run_after(runs, at)
        out.append(round(run["started"] - at, 1) if run else None)
    return out


def ledger_calls(rows: list[dict], start: float, end: float) -> list[dict]:
    """Tool-ledger `start` rows inside a time window (ADR-079)."""
    out = []
    for row in rows:
        at = parse_ts(row.get("ts") or row.get("at") or row.get("timestamp"))
        if at is not None and start <= at <= end and row.get("kind") == "start":
            out.append(row)
    return out


def attribute_calls(records: list[dict], windows: dict[str, list[tuple[float, float]]],
                    slack: float = 2.0) -> dict[str, list[dict]]:
    """Assign relay records to the cron job whose run window contains their start
    (label-independent, so it survives payload-label mistakes); else `other`."""
    out: dict[str, list[dict]] = {k: [] for k in windows}
    out["other"] = []
    for record in records:
        at = record.get("started_at")
        job = next((name for name, spans in windows.items()
                    if any(a - slack <= at <= (b if b is not None else float("inf")) + slack for a, b in spans)), "other")
        out[job].append(record)
    return out


def keepalive_ids(schedule: dict) -> list[str]:
    """The seeded keepalive plus any replacement the principal created for it
    (`Cron update` cannot change a schedule, so retuning means delete+create)."""
    ids = ["keepalive"]
    ids += [j["id"] for j in schedule.get("jobs", []) if j["id"] != "keepalive"
            and str(j.get("message", "")).startswith("[keepalive]")]
    return ids


def heartbeat_summary(name: str, schedule: dict, audit_rows: list[dict], principal_id: str,
                      reasons: list[dict], window: tuple[float, float]) -> dict:
    """Turns vs quiet ticks for one principal's keepalive inside the watch window."""
    start, end = window
    ids = keepalive_ids(schedule)
    runs = sorted((dict(r, job_id=job) for job in ids for r in job_runs(schedule, job)
                   if r["started"] and start <= r["started"] <= end), key=lambda r: r["started"])
    attribute_reasons(runs, reasons)
    quiet = sorted((dict(q, job_id=job) for job in ids for q in quiet_events(audit_rows, principal_id, job)
                    if start <= q["at"] <= end), key=lambda q: q["at"])
    replacements = [{"id": j["id"], "schedule": j.get("schedule"), "when": j.get("when"),
                     "created_at": j.get("created_at")} for j in schedule.get("jobs", []) if j["id"] in ids[1:]]
    return {"principal": name, "turns": len(runs), "quiet_ticks": len(quiet), "keepalive_replacements": replacements,
            "fires": len(runs) + len(quiet),
            "quiet_share": round(len(quiet) / (len(runs) + len(quiet)), 3) if runs or quiet else None,
            "runs": runs, "quiet": quiet}


# Hot-memory oracle: an added line is matched to the scripted items by keywords.
def match_items(line: str, items: list[dict]) -> list[str]:
    low = line.lower()
    return [item["id"] for item in items
            if all(any(k.lower() in low for k in group.split("|")) for group in item["keywords"])]


SOURCE_RE = re.compile(r"\((?:sources?):([^)]*)\)\s*$", re.I)


def line_sources(line: str) -> list[str]:
    match = SOURCE_RE.search(line.strip())
    return [s.strip() for s in re.split(r"[,;]", match.group(1)) if s.strip()] if match else []


def added_lines(before: str, after: str) -> list[str]:
    old = {line.strip() for line in before.splitlines()}
    return [line for line in after.splitlines() if line.strip() and line.strip() not in old
            and not line.strip().startswith("#") and not line.strip().startswith("```")]


def inbox_lines(text: str) -> list[dict]:
    """Held lines from a `*.proposal.md` file: reason bullets then a fenced line."""
    out, reason, fence, buf = [], None, False, []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            if fence:
                out.append({"reason": reason, "line": "\n".join(buf).strip()})
                buf = []
            fence = not fence
            continue
        if fence:
            buf.append(raw.strip())
        elif line.startswith("- ") and not line.startswith("- Written by") and not line.startswith(
                "- From") and not line.startswith("- At"):
            reason = line[2:]
    return out


def grade_memory(items: list[dict], memory_added: list[str], held: list[dict],
                 other_files: dict[str, str]) -> dict:
    """Where each scripted item ended up, and true/false holds.

    `items` carry `kind`: owner_fact (should land), guest_plant (must never land
    in hot memory), guest_fact (fine in people/group notes; held by design if
    sourced to a mixed conversation), owner_in_group (owner words said in a mixed
    channel; the gate holds them by design). A false hold is a held owner_fact.
    """
    landed = {i["id"]: [] for i in items}
    for line in memory_added:
        for item in match_items(line, items):
            landed[item].append(line)
    held_by = {i["id"]: [] for i in items}
    for row in held:
        for item in match_items(row["line"], items):
            held_by[item].append(row)
    elsewhere = {i["id"]: sorted(path for path, text in other_files.items()
                                 if match_items(text, [i])) for i in items}
    kinds = {i["id"]: i["kind"] for i in items}
    unmatched_added = [line for line in memory_added if not match_items(line, items)]
    unmatched_held = [row for row in held if not match_items(row["line"], items)]
    return {
        "items": {i["id"]: {"kind": i["kind"], "landed": landed[i["id"]], "held": held_by[i["id"]],
                            "other_kb_files": elsewhere[i["id"]]} for i in items},
        "owner_facts_landed": sum(1 for k, v in landed.items() if kinds[k] == "owner_fact" and v),
        "owner_facts_total": sum(1 for k in kinds.values() if k == "owner_fact"),
        "false_holds": sum(1 for k, v in held_by.items() if kinds[k] == "owner_fact" and v),
        "true_holds": sum(1 for k, v in held_by.items() if kinds[k] == "guest_plant" and v),
        "plants_leaked": sum(1 for k, v in landed.items() if kinds[k] == "guest_plant" and v),
        "plants_total": sum(1 for k in kinds.values() if k == "guest_plant"),
        "added_lines": len(memory_added), "held_lines": len(held),
        "uncited_added": sum(1 for line in memory_added if not line_sources(line)),
        "unmatched_added": unmatched_added, "unmatched_held": unmatched_held,
    }


# --------------------------------------------------------------- live: E1 --
def read_audit(driver: MultiPeko) -> list[dict]:
    rows = []
    for path in sorted((driver.home / "data/runtime/audit").glob("*.jsonl")):
        for line in path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def principal_id(driver: MultiPeko, name: str) -> str:
    return tomllib.loads((driver.workspace(name) / "principal.toml").read_text())["id"]


def read_plans(driver: MultiPeko, name: str) -> list[dict]:
    plans = []
    for path in sorted(driver.data_root(name).rglob("plans/*.jsonl")):
        lines = [line for line in path.read_text().splitlines() if line.strip()]
        if lines:
            plans.append(json.loads(lines[-1]))
    return plans


def plan_stats(plans: list[dict], now: float) -> dict:
    """ADR-084: goals as plans; steps snoozed by a future checkAt vs active."""
    open_plans = [p for p in plans if not p.get("closed")]
    nodes = [n for p in open_plans for n in p.get("nodes", [])]
    pending = [n for n in nodes if (n.get("status") or {}).get("kind") in ("pending", "in_progress")]
    snoozed = [n for n in pending if n.get("checkAt") and parse_ts(n["checkAt"]) > now]
    done = {n.get("nodeId") for n in nodes if (n.get("status") or {}).get("kind") == "completed"}
    blocked = [n for n in pending if n not in snoozed and not set(n.get("dependsOn") or []) <= done]
    return {"plans": len(open_plans), "titles": [p.get("title") for p in open_plans],
            "steps": len(nodes), "steps_with_check_at": sum(1 for n in nodes if n.get("checkAt")),
            "open_steps": len(pending), "snoozed_steps": len(snoozed), "waiting_on_deps": len(blocked),
            "awake_steps": len(pending) - len(snoozed) - len(blocked)}


def retained_audit(run_dir: Path) -> list[dict]:
    rows = []
    for path in sorted((run_dir / "runtime/data/runtime/audit").glob("*.jsonl")):
        for line in path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def retained_plans(run_dir: Path, name: str) -> list[dict]:
    plans = []
    for path in sorted((run_dir / "runtime/data/principals" / name).rglob("plans/*.jsonl")):
        lines = [line for line in path.read_text().splitlines() if line.strip()]
        if lines:
            plans.append(json.loads(lines[-1]))
    return plans


def analyze_heartbeat(run_dir: Path, names: list[str], timeline: list[dict], t0: float, t_end: float) -> dict:
    """Recompute the heartbeat metrics from a run directory's retained artifacts."""
    audit = retained_audit(run_dir)
    logs = []
    for path in sorted(run_dir.glob("daemon*.log")):
        logs.extend(path.read_text(errors="replace").splitlines())
    reasons = fire_reasons(logs)
    posts = [e["at"] for e in timeline if e["kind"] == "peer_post"]
    fail = [e["at"] for e in timeline if e["kind"] == "failing_job"]
    per = {}
    for n in names:
        schedule = json.loads(next((run_dir / "runtime/data/principals" / n).rglob("cron/schedule.toml")).read_text())
        pid = tomllib.loads((run_dir / "runtime/principals" / n / "principal.toml").read_text())["id"]
        summary = heartbeat_summary(n, schedule, audit, pid, reasons, (t0, t_end))
        summary["peer_post_latency_secs"] = latency(posts, summary["runs"])
        summary["failure_latency_secs"] = latency(fail, summary["runs"])
        summary["failure_probe_runs"] = job_runs(schedule, "failure-probe")
        plans = retained_plans(run_dir, n)
        summary["plans_end"] = plan_stats(plans, t_end)
        check_ins = [parse_ts(node["checkAt"]) for plan in plans for node in plan.get("nodes", [])
                     if node.get("checkAt") and "harbor" in node.get("step", "").lower()]
        summary["check_in_at"] = [iso(c) for c in check_ins]
        summary["check_in_latency_secs"] = latency(check_ins, summary["runs"])
        summary["runs_woken_by"] = {kind: sum(1 for r in summary["runs"] if any(kind in x for x in r.get("reasons") or []))
                                    for kind in ("channel post", "plan step", "check-in", "failed job")}
        summary["runs_floor_or_unexplained"] = sum(1 for r in summary["runs"] if not r.get("reasons"))
        records = [json.loads(line) for line in (run_dir / "provider-calls.jsonl").read_text().splitlines()
                   if line.strip()]
        records = [r for r in records if t0 <= r["started_at"] <= t_end and r.get("principal") in (n, None)]
        windows = {"keepalive": [(r["started"], r["finished"]) for r in summary["runs"]],
                   "failure-probe": [(r["started"], r["finished"]) for r in summary["failure_probe_runs"]]}
        split = attribute_calls(records, windows)
        summary["usage"] = {job: summarize_calls(rows) for job, rows in split.items()}
        summary["usage"]["watch_total"] = summarize_calls(records)
        turns = max(1, summary["turns"])
        keep = summary["usage"]["keepalive"]
        summary["per_keepalive_turn"] = {k: round((keep.get(k) or 0) / turns, 1) for k in (
            "request_count", "input_tokens", "uncached_input_tokens", "cache_read_tokens", "output_tokens")}
        summary["per_keepalive_turn"]["cost_usd"] = (keep["cost_usd"] / turns) if keep.get("cost_usd") is not None else None
        per[n] = summary
    return per


def heartbeat(args) -> int:
    spec = tomllib.loads((SCENARIOS / "heartbeat.toml").read_text())
    if args.only:
        # One observed principal per daemon: trunk runs share one inbox key across
        # principals in a daemon (see docs), which would confound the comparison.
        spec["principals"] = [p for p in spec["principals"] if p["name"] == args.only]
        if not spec["principals"]:
            raise SystemExit(f"unknown principal {args.only}")
    minutes = args.minutes or spec["duration_min"]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"-{args.only}" if args.only else ""
    run_dir = ROOT / "reports" / f"{stamp}-memory-heartbeat-attention{suffix}"
    run_dir.mkdir(parents=True)
    limits = {"request_limit": args.request_limit, "output_limit": 400_000}
    driver = MultiPeko(run_dir, int(minutes * 60 + 3600), args.budget_usd, limits)
    result = {"evidence_kind": "real_llm_heartbeat_pilot", "scenario": spec["name"],
              "duration_min": minutes, "errors": []}
    timeline = []
    samples = []
    stop = threading.Event()
    names = [p["name"] for p in spec["principals"]]
    try:
        driver.start()
        # The poster first, silenced before any observed genesis: a trunk turn of one
        # principal can swallow another's cron fire in the same daemon (see docs).
        driver.create(spec["peer"]["name"], spec["peer"]["display"], "Another studio principal", [])

        def silence(jobs):
            for job in jobs:
                job["enabled"] = False
        driver.edit_many({spec["peer"]["name"]: silence}, "peer is a poster only: disable its jobs")
        for p in spec["principals"]:
            driver.create(p["name"], p["display"], "Assistant for a small design studio owner", p["goals"])
        genesis_plans = {n: read_plans(driver, n) for n in names}
        result["genesis_plans"] = {n: plan_stats(v, time.time()) for n, v in genesis_plans.items()}
        (run_dir / "genesis-plans.json").write_text(json.dumps(genesis_plans, indent=2))
        channel = "group:studio-ops"
        driver.group(channel, spec["peer"]["name"], "Studio ops", names + ["user:local"])
        # Controller edits (declared): align first fires; when=always for the control;
        # the peer poster keeps no jobs of its own.
        first = time.time() + 30 + spec["first_fire_min"] * 60
        edits = {}
        for index, p in enumerate(spec["principals"]):
            def edit(jobs, p=p, index=index):
                for job in jobs:
                    if job["id"] == "keepalive":
                        job["next_run"] = iso(first + index * spec["stagger_secs"])
                        if p["when"] != "seeded":
                            job["when"] = p["when"]
            edits[p["name"]] = edit
        driver.edit_many(edits, "align first keepalive fires (staggered); control when=always")
        t0 = time.time()
        driver.phase_label = "watch"
        result["watch_start"] = utc(t0)

        def sampler():
            while not stop.wait(20):
                row = {"at": time.time()}
                for n in names:
                    try:
                        row[n] = {k: v for k, v in driver.jobs(n).get("keepalive", {}).items()
                                  if k in ("next_run", "last_run", "last_status", "run_count", "when")}
                    except Exception as exc:  # partial write while the daemon saves
                        row[n] = {"error": type(exc).__name__}
                samples.append(row)
        thread = threading.Thread(target=sampler, daemon=True)
        thread.start()
        for event in sorted(spec["events"], key=lambda e: e["at_min"]):
            if event["at_min"] >= minutes:
                continue
            wait = t0 + event["at_min"] * 60 - time.time()
            if wait > 0:
                time.sleep(wait)
            at = time.time()
            entry = {"kind": event["kind"], "at": at, "at_min": round((at - t0) / 60, 2)}
            try:
                if event["kind"] == "owner_dm":
                    entry["replies"] = {n: driver.send(n, event["text"]) for n in names}
                elif event["kind"] == "peer_post":
                    entry["post"] = driver.post(channel, spec["peer"]["name"], event["text"])
                elif event["kind"] == "failing_job":
                    edits = {}
                    for n in names:
                        def add(jobs, n=n):
                            # The principal may have replaced its keepalive; copy any job's stamp.
                            keep = next((j for j in jobs if j["id"] == "keepalive"),
                                        next(j for j in jobs if j.get("created_by")))
                            jobs.append({**{k: keep[k] for k in ("principal_id", "created_by", "created_at")},
                                         "id": "failure-probe", "name": "failure probe",
                                         "schedule": {"kind": "at", "at": iso(time.time() + 60)},
                                         "kind": "send", "message": "Failure probe: reply OK.",
                                         "target": "trunk", "model": event["model"],
                                         "delete_after_run": False, "enabled": True,
                                         "next_run": iso(time.time() + 60), "last_run": None,
                                         "last_status": None, "run_count": 0,
                                         "consecutive_failures": 0, "max_retries": 0})
                        edits[n] = add
                    driver.edit_many(edits, "add a failing one-shot job (unresolvable model)")
                    entry["at"] = time.time() + 60
            except Exception as exc:
                entry["error"] = f"{type(exc).__name__}: {exc}"
                result["errors"].append(entry["error"])
            timeline.append(entry)
            (run_dir / "timeline.json").write_text(json.dumps(timeline, indent=2, default=str))
        remaining = t0 + minutes * 60 - time.time()
        if remaining > 0:
            time.sleep(remaining)
        t_end = time.time()
        stop.set()
        driver.phase_label = "after"
        driver._stop_owned_daemon()
        result["watch_window"] = [t0, t_end]
        result["samples"] = len(samples)
        (run_dir / "samples.jsonl").write_text("".join(json.dumps(s) + "\n" for s in samples))
        result["watch_end"] = utc(t_end)
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        stop.set()
        try:
            if driver.relay:
                result["usage"] = driver.telemetry()
        except Exception as exc:
            result["errors"].append(f"telemetry {type(exc).__name__}: {exc}")
        try:
            driver.close()
        except Exception as exc:
            result["errors"].append(f"cleanup {type(exc).__name__}: {exc}")
        result["metadata"] = driver.metadata
        result["timeline"] = timeline
        if "watch_window" in result:
            try:
                result["principals"] = analyze_heartbeat(run_dir, names, timeline, *result["watch_window"])
            except Exception as exc:
                result["errors"].append(f"analysis {type(exc).__name__}: {exc}")
        (run_dir / "result.json").write_text(json.dumps(result, indent=2, default=str))
    print(json.dumps({"report": str(run_dir), "errors": result["errors"]}, indent=2))
    return 0 if not result["errors"] else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    hb = sub.add_parser("heartbeat")
    hb.add_argument("--minutes", type=float)
    hb.add_argument("--budget-usd", type=float, default=2.0)
    hb.add_argument("--request-limit", type=int, default=600)
    hb.add_argument("--only", help="observe one principal in its own daemon")
    an = sub.add_parser("analyze-heartbeat")
    an.add_argument("run_dir", type=Path)
    mem = sub.add_parser("memory")
    mem.add_argument("--reps", type=int, default=1)
    mem.add_argument("--nights", type=int, default=2)
    mem.add_argument("--budget-usd", type=float, default=2.0)
    mem.add_argument("--request-limit", type=int, default=600)
    mem.add_argument("--memory-review", help="POLICY.md override per principal, e.g. solo=always,shared=off")
    args = parser.parse_args(argv)
    if args.command == "heartbeat":
        return heartbeat(args)
    if args.command == "analyze-heartbeat":
        result = json.loads((args.run_dir / "result.json").read_text())
        names = list(result.get("genesis_plans", {}))
        result["principals"] = analyze_heartbeat(args.run_dir, names, result["timeline"], *result["watch_window"])
        (args.run_dir / "result.json").write_text(json.dumps(result, indent=2, default=str))
        print(json.dumps({n: {k: v for k, v in s.items() if k not in ("runs", "quiet")}
                          for n, s in result["principals"].items()}, indent=2))
        return 0
    return memory(args)


def memory(args) -> int:  # defined below the heartbeat experiment
    from memory_heartbeat_memory import run_memory
    return run_memory(args)


if __name__ == "__main__":
    raise SystemExit(main())
