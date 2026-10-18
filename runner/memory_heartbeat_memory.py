"""Nightly memory pass and its gates on live principals (ADR-080 rev 2/3, ADR-085).

Per replicate: one isolated daemon with an owner-only principal (`solo`), a
principal that also talks in a group with a guest principal (`shared`), and the
guest (a poster only: `peko channel post`, no model call). Keepalives are
disabled so the forced nightly pass is the only scheduled writer. Each night:
the scripted owner DMs (and group posts), a zero-cost D9 hold check, then the
controller sets the memory job due with `when: always` (declared) so it fires
now; the runtime still supplies the brief at fire time.
"""
from __future__ import annotations

import datetime as dt
import json
import time
import tomllib
from pathlib import Path

from memory_heartbeat_peko import MultiPeko, utc
from memory_heartbeat import (ROOT, SCENARIOS, added_lines, grade_memory, inbox_lines, iso, match_items,
                              job_runs, parse_ts, plan_stats, read_plans, read_audit,
                              principal_id, quiet_events)
from continuity_proxy import summarize_calls

HOT = ("kb/MEMORY.md", "kb/CONVENTIONS.md")


MEMORY_MARKER_PREFIX = "[memory] Daily memory maintenance. The runtime supplies the current brief"


def memory_job(jobs: dict) -> dict | None:
    """The nightly memory job: the seeded `memory`, or the one a principal
    recreated under another id (genesis may delete and recreate it)."""
    if "memory" in jobs:
        return jobs["memory"]
    found = [j for j in jobs.values() if j.get("kind") == "send"
             and ((j.get("message") or "").startswith("[memory]") or "memory" in (j.get("name") or "").lower())]
    return found[0] if found else None


def describe_memory_job(job: dict | None) -> dict:
    if job is None:
        return {"present": False}
    return {"present": True, "id": job["id"], "seeded_id": job["id"] == "memory",
            "runtime_brief": (job.get("message") or "").startswith(MEMORY_MARKER_PREFIX),
            "schedule": job.get("schedule"), "when": job.get("when"), "model": job.get("model"),
            "enabled": job.get("enabled"), "message_chars": len(job.get("message") or "")}


def stale_lines(items: list[dict], memory: str) -> dict[str, list[str]]:
    """Lines still stating a superseded value (a line that also carries the
    replacement, e.g. "raised from 6,000 to 9,500", records the change)."""
    by_id = {i["id"]: i for i in items}
    out = {}
    for item in items:
        if item["kind"] != "stale":
            continue
        newer = by_id.get(item.get("superseded_by", ""))
        out[item["id"]] = [entry for entry in entries(memory) if match_items(entry, [item])
                           and not (newer and match_items(entry, [newer]))]
    return out


def held_entries(rows: list[dict]) -> list[dict]:
    """Rejoin held physical lines of one proposal into entries ("- " starts one);
    the reason of an entry is that of its last line (where a source would be)."""
    out: list[dict] = []
    for row in rows:
        text = row["line"].strip()
        if out and out[-1]["file"] == row["file"] and not text.startswith("- ") and not out[-1]["closed"]:
            out[-1]["line"] += " " + text
            out[-1]["reasons"].append(row["reason"])
        else:
            out.append({"line": text, "file": row["file"], "reasons": [row["reason"]], "closed": False})
        out[-1]["closed"] = "(source" in text.lower()
    return [{"line": e["line"], "file": e["file"], "reason": e["reasons"][-1],
             "physical_lines": len(e["reasons"])} for e in out]


def entries(text: str) -> list[str]:
    """Markdown entries: a line plus its indented continuation lines."""
    out: list[str] = []
    for line in text.splitlines():
        if out and line[:1] in (" ", "\t") and line.strip():
            out[-1] += " " + line.strip()
        elif line.strip():
            out.append(line.strip())
    return out


def grade_night(items: list[dict], b: dict[str, str], a: dict[str, str]) -> dict:
    """What one pass changed, from kb snapshots before and after it."""
    # Entry level (a bullet plus its wrapped continuation lines), because the
    # runtime gate screens physical lines while the model writes wrapped entries.
    hot_added = {f: [e for e in entries(a.get(f, "")) if e not in set(entries(b.get(f, "")))
                     and not e.startswith("#")] for f in HOT}
    physical = {f: added_lines(b.get(f, ""), a.get(f, "")) for f in HOT}
    removed = {f: [l for l in b.get(f, "").splitlines() if l.strip() and l.strip() not in
                   {x.strip() for x in a.get(f, "").splitlines()}] for f in HOT}
    held_lines = new_inbox(b, a)
    held = held_entries(held_lines)
    others = {p: t for p, t in a.items() if p not in HOT and not p.startswith("kb/inbox/") and t != b.get(p)}
    final = {f: a.get(f, "") for f in HOT}
    present = {}
    for label, snap in (("before", b), ("after", a)):
        hot_entries = [e for f in HOT for e in entries(snap.get(f, ""))]
        present[label] = sorted({i for e in hot_entries for i in match_items(e, items)
                                 if any(x["id"] == i and x["kind"] == "owner_fact" for x in items)})
    before_entries = [e for e in entries(b.get(HOT[0], "")) if e.startswith("- ")]
    after_entries = [e for e in entries(a.get(HOT[0], "")) if e.startswith("- ")]
    truncated = [e for e in after_entries if e not in before_entries
                 and any(o.startswith(e) and len(o) > len(e) for o in before_entries)]
    return {"owner_facts_in_hot": present,
            "owner_facts_lost": sorted(set(present["before"]) - set(present["after"])),
            "memory_entries_truncated": truncated,"hot_added": hot_added, "hot_removed": removed, "held": held,
            "physical_lines": {"hot_added": sum(len(v) for v in physical.values()), "held": len(held_lines)},
            "grade": grade_memory(items, hot_added["kb/MEMORY.md"] + hot_added["kb/CONVENTIONS.md"], held, others),
            "files_written": sorted(p for p in a if a[p] != b.get(p)),
            "stale_left_in_memory": stale_lines(items, final["kb/MEMORY.md"]),
            "memory_bytes": len(final["kb/MEMORY.md"].encode()),
            "conventions_bytes": len(final["kb/CONVENTIONS.md"].encode()),
            "truncation_notice": "truncat" in final["kb/MEMORY.md"].lower(),
            "dream_files": [p for p in a if p.startswith("kb/dreams/") and not p.endswith("README.md")],
            "journal_files": [p for p in a if p.startswith("kb/journal/")]}


def regrade(rep_dir: Path) -> dict:
    """Recompute every night's grade from the retained kb snapshots."""
    spec = tomllib.loads((SCENARIOS / "memory.toml").read_text())
    result = json.loads((rep_dir / "result.json").read_text())
    for night in result.get("nights", []):
        for name, row in night["principals"].items():
            prefix = rep_dir / f"kb-{name}-night{night['night']}"
            if Path(f"{prefix}-before.json").is_file():
                row.update(grade_night(spec["items"], json.loads(Path(f"{prefix}-before.json").read_text()),
                                       json.loads(Path(f"{prefix}-after.json").read_text())))
    return result


def snapshot(workspace: Path) -> dict[str, str]:
    kb = workspace / "kb"
    return {str(p.relative_to(workspace)): p.read_text(errors="replace")
            for p in sorted(kb.rglob("*.md")) if p.is_file()}


def new_inbox(before: dict, after: dict) -> list[dict]:
    rows = []
    for path, text in after.items():
        if path.startswith("kb/inbox/") and path not in before:
            for row in inbox_lines(text):
                rows.append({**row, "file": path})
    return rows


def wait_for_run(driver: MultiPeko, name: str, job_id: str, count: int, timeout: float) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            runs = job_runs(json.loads(driver.schedule_path(name).read_text()), job_id)
        except (json.JSONDecodeError, ValueError):
            runs = []
        done = [r for r in runs if r["finished"]]
        if len(done) >= count:
            return done[-1]
        time.sleep(10)
    return None


def night(driver: MultiPeko, spec: dict, day: dict, index: int, run_dir: Path, names: list[str],
          channel: str) -> dict:
    out = {"night": index + 1, "principals": {}}
    driver.phase_label = f"day{index + 1}"
    for name in names:
        replies = []
        for text in day["owner_dm"]:
            try:
                replies.append(driver.send(name, text))
            except Exception as exc:
                replies.append({"error": f"{type(exc).__name__}: {exc}"})
        out["principals"][name] = {"dm_replies": replies}
    group_posts = []
    for post in day.get("group", []):
        sender = "me" if post["sender"] == "me" else spec["guest"]["name"]
        try:
            group_posts.append(driver.post(channel, sender, post["text"]))
        except Exception as exc:
            group_posts.append({"error": f"{type(exc).__name__}: {exc}"})
        # A mention wakes the bot; let that turn finish before the next post.
        time.sleep(45 if post["sender"] == "me" else 3)
    out["group_posts"] = group_posts
    time.sleep(20)
    before = {n: snapshot(driver.workspace(n)) for n in names}
    # ADR-080 D9 hold check (no model call): due now, but someone just talked.
    ids = {n: (memory_job(driver.jobs(n)) or {}).get("id") for n in names}
    out["memory_job"] = {n: describe_memory_job(memory_job(driver.jobs(n))) for n in names}

    def due_quiet(jobs):
        for job in jobs:
            if job["id"] in ids.values():
                job["next_run"] = iso(time.time())
                job["when"] = "quiet"
    driver.edit_many({n: due_quiet for n in names}, "D9 check: memory job due now, when=quiet")
    time.sleep(25)
    hold = {}
    for n in names:
        job = driver.jobs(n).get(ids[n])
        if job is None:
            hold[n] = {"error": "no memory job"}
            continue
        hold[n] = {"last_status": job.get("last_status"), "next_run": job.get("next_run"),
                   "held_hours": round((parse_ts(job["next_run"]) - time.time()) / 3600, 2)}
    out["d9_hold"] = hold
    # Force the pass (declared controller edit): due now, when=always.
    def due_now(jobs):
        for job in jobs:
            if job["id"] in ids.values():
                job["next_run"] = iso(time.time() + 10)
                job["when"] = "always"
    driver.phase_label = f"night{index + 1}"
    started = time.time()
    for n in names:  # one pass at a time (shared trunk inbox key; see docs)
        if not ids[n]:
            out["principals"][n]["memory_run"] = None
            continue
        driver.edit_many({n: due_now}, f"night {index + 1}: force memory pass (when=always)")
        out["principals"][n]["memory_run"] = wait_for_run(driver, n, ids[n], index + 1, 1500)
    after = {n: snapshot(driver.workspace(n)) for n in names}
    items = spec["items"]
    for n in names:
        b, a = before[n], after[n]
        out["principals"][n].update(grade_night(items, b, a))
        (run_dir / f"kb-{n}-night{index + 1}-before.json").write_text(json.dumps(b, indent=2))
        (run_dir / f"kb-{n}-night{index + 1}-after.json").write_text(json.dumps(a, indent=2))
    out["window"] = [started, time.time()]
    return out


def replicate(spec: dict, args, rep: int, parent: Path) -> dict:
    run_dir = parent / f"rep{rep + 1}"
    run_dir.mkdir()
    limits = {"request_limit": args.request_limit, "output_limit": 600_000}
    driver = MultiPeko(run_dir, 4 * 3600, args.budget_usd, limits)
    result = {"rep": rep + 1, "errors": [], "nights": []}
    principals = spec["principals"]
    names = [p["name"] for p in principals]
    channel = "group:vendors"
    try:
        driver.start()
        setup = spec["setup"]

        def silence(jobs):
            for job in jobs:
                job["enabled"] = False

        def quiet_jobs(jobs):
            for job in jobs:
                if job["id"] == "keepalive":
                    job["enabled"] = False
        # One trunk turn at a time: in one daemon a busy trunk can swallow another
        # principal's cron fire (see docs). The guest first, silenced; each observed
        # principal loses its keepalive right after genesis (the pass is the only
        # scheduled writer under test).
        driver.create(spec["guest"]["name"], spec["guest"]["display"], "Billing coordinator at Harbor Print", [])
        driver.edit_many({spec["guest"]["name"]: silence}, "guest is a poster only: disable its jobs")
        for p in principals:
            driver.create(p["name"], p["display"], setup["description"], setup["goals"])
            driver.edit_many({p["name"]: quiet_jobs}, "disable keepalive after genesis")
        result["genesis_plans"] = {n: plan_stats(read_plans(driver, n), time.time()) for n in names}
        result["memory_job_after_genesis"] = {n: describe_memory_job(memory_job(driver.jobs(n))) for n in names}
        result["genesis_inbox"] = {n: [p for p in snapshot(driver.workspace(n)) if p.startswith("kb/inbox/")]
                                   for n in names}
        # Optional review-setting variant (ADR-085 D4), written into POLICY.md front matter.
        overrides = dict(v.split("=", 1) for v in (args.memory_review or "").split(",") if "=" in v)
        for name, value in overrides.items():
            path = driver.workspace(name) / "POLICY.md"
            text = path.read_text()
            new_text, count = __import__("re").subn(r"(?m)^memory_review:\s*\S+", f"memory_review: {value}", text)
            if not count:
                raise ValueError(f"no memory_review key in {name}'s POLICY.md")
            path.write_text(new_text)
        result["memory_review_overrides"] = overrides
        grouped = [p["name"] for p in principals if p["group"]]
        driver.group(channel, spec["guest"]["name"], "Harbor Print billing", grouped + ["user:local"])
        for n in names:
            path = driver.workspace(n) / "kb/MEMORY.md"
            path.write_text(path.read_text().rstrip("\n") + "\n\n" + setup["stale_memory_line"] + "\n")
        for index, day in enumerate(spec["days"][:args.nights]):
            # The group exists only for `shared`; `solo` gets the DMs alone.
            result["nights"].append(night(driver, spec, day, index, run_dir, names, channel))
            (run_dir / "partial.json").write_text(json.dumps(result, indent=2, default=str))
        driver._stop_owned_daemon()
        audit = read_audit(driver)
        result["memory_quiet_events"] = {n: [q for job in driver.jobs(n).values()
                                             for q in quiet_events(audit, principal_id(driver, n), job["id"])
                                             if job["id"] != "keepalive"] for n in names}
        result["plans_end"] = {n: plan_stats(read_plans(driver, n), time.time()) for n in names}
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        try:
            if driver.relay:
                result["usage"] = driver.telemetry()
                rows = driver.records()
                result["reviewer_calls"] = {
                    night["night"]: summarize_calls([r for r in rows if r.get("call_kind") == "memory_review"
                                                     and night["window"][0] <= r["started_at"] <= night["window"][1]])
                    for night in result["nights"] if "window" in night}
        except Exception as exc:
            result["errors"].append(f"telemetry {type(exc).__name__}: {exc}")
        try:
            driver.close()
        except Exception as exc:
            result["errors"].append(f"cleanup {type(exc).__name__}: {exc}")
        result["metadata"] = driver.metadata
        (run_dir / "result.json").write_text(json.dumps(result, indent=2, default=str))
    return result


def run_memory(args) -> int:
    spec = tomllib.loads((SCENARIOS / "memory.toml").read_text())
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parent = ROOT / "reports" / f"{stamp}-memory-heartbeat-nightly"
    parent.mkdir(parents=True)
    results = [replicate(spec, args, rep, parent) for rep in range(args.reps)]
    errors = [e for r in results for e in r["errors"]]
    (parent / "summary.json").write_text(json.dumps({"reps": len(results), "errors": errors,
                                                     "finished": utc()}, indent=2))
    print(json.dumps({"report": str(parent), "errors": errors}, indent=2))
    return 0 if not errors else 1
