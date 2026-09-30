#!/usr/bin/env python3
"""peko-benchmark matrix runner.

Runs a matrix of (task × harness × rep), grades each run deterministically,
and writes a report directory under reports/:

    reports/<utc-timestamp>[-<tag>]/
      results.jsonl                       # one JSON record per run
      summary.md                          # human-readable aggregate
      summary.json                        # machine-readable aggregate
      <task-id>/<harness>/run<N>/
        work/                             # the fixture the agent worked on
        prompt.txt                        # exact prompt sent
        transcript.txt                    # harness transcript (from harness)
        harness.log                       # harness stdout/stderr
        harness_meta.json                 # rc, wall time, completion flag
        grade.txt                         # grader output
        result.json                       # the run's results.jsonl record

Usage:
    python3 runner/run.py --list
    python3 runner/run.py --tasks bugfix/py-cache-invalidation --harnesses peko
    python3 runner/run.py --tasks all --harnesses peko,codex --reps 3 --tag pre-mvp

Requires python >= 3.11 (stdlib tomllib).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    sys.stderr.write("error: python >= 3.11 required (stdlib tomllib missing)\n")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"
HARNESSES_DIR = REPO_ROOT / "harnesses"
REPORTS_DIR = REPO_ROOT / "reports"

# The workdir path leads the prompt: a peko agent's default cwd is its own
# (empty) workspace, and a suffix-only note wastes iterations on "the
# directory is empty" exploration (observed in the first smoke run).
PROMPT_PREFIX = (
    "Working directory: `{work}` — the task project is already there.\n"
    "Make ALL changes inside that directory (use absolute paths, or pass it\n"
    "as the working directory for shell commands). Your own home/workspace\n"
    "directory is unrelated to this task; do not look for the project there.\n\n"
)
PROMPT_SUFFIX = (
    "\n\n---\n"
    "Reminder: work only inside `{work}`. You have shell access — run the\n"
    "relevant tests/commands to verify your work before finishing.\n"
)

# Extra wall-clock grace on top of the task's timeout before the runner
# kills a stuck harness outright.
HARNESS_GRACE_SECS = 120


class TaskError(Exception):
    pass


def load_task(task_dir: Path) -> dict:
    spec_path = task_dir / "task.toml"
    if not spec_path.is_file():
        raise TaskError(f"missing task.toml in {task_dir}")
    with spec_path.open("rb") as fh:
        spec = tomllib.load(fh)

    prompt = spec.get("prompt")
    if prompt is None and spec.get("prompt_file"):
        prompt_file = task_dir / spec["prompt_file"]
        if not prompt_file.is_file():
            raise TaskError(f"{task_dir}: prompt_file not found: {prompt_file}")
        prompt = prompt_file.read_text()
    if not prompt or not prompt.strip():
        raise TaskError(f"{task_dir}: task.toml needs a non-empty prompt or prompt_file")

    grade = task_dir / "grade.sh"
    if not grade.is_file():
        raise TaskError(f"{task_dir}: missing grade.sh")

    return {
        "id": spec.get("id", task_dir.name),
        "field": spec.get("field", task_dir.parent.name),
        "description": spec.get("description", ""),
        "timeout_secs": int(spec.get("timeout_secs", 600)),
        "prompt": prompt,
        "dir": task_dir,
        "fixture": task_dir / "fixture",
        "grade": grade,
        "setup": task_dir / "setup.sh",
    }


def discover_tasks(selection: list[str]) -> list[dict]:
    all_dirs = sorted(
        p.parent for p in TASKS_DIR.glob("*/*/task.toml")
    )
    if selection == ["all"]:
        chosen = all_dirs
    else:
        chosen = []
        for sel in selection:
            match = TASKS_DIR / sel
            if match.is_dir():
                chosen.append(match)
                continue
            by_id = [d for d in all_dirs if d.name == sel]
            if by_id:
                chosen.extend(by_id)
            else:
                raise TaskError(
                    f"unknown task {sel!r} — expected a path like "
                    f"'bugfix/py-cache-invalidation' or a task id; "
                    f"see --list"
                )
    return [load_task(d) for d in chosen]


def list_tasks() -> None:
    for task_dir in sorted(TASKS_DIR.glob("*/*/task.toml")):
        task = load_task(task_dir.parent)
        rel = task_dir.parent.parent.name + "/" + task_dir.parent.name
        print(f"{rel:45s} {task['description']}")


def setup_workdir(task: dict, work: Path) -> None:
    """Populate the per-run workdir from the task fixture."""
    work.mkdir(parents=True, exist_ok=True)
    if task["setup"].is_file():
        subprocess.run(
            ["bash", str(task["setup"]), str(task["dir"]), str(work)],
            check=True,
        )
    elif task["fixture"].is_dir():
        shutil.copytree(task["fixture"], work, dirs_exist_ok=True)
    else:
        raise TaskError(f"{task['dir']}: no fixture/ and no setup.sh")


def parse_score_json(grade_output: str) -> dict:
    for line in reversed(grade_output.splitlines()):
        line = line.strip()
        if line.startswith("SCORE_JSON "):
            try:
                return json.loads(line[len("SCORE_JSON "):])
            except json.JSONDecodeError as exc:
                return {
                    "passed": False,
                    "score": 0.0,
                    "details": f"grader emitted invalid SCORE_JSON: {exc}",
                }
    return {
        "passed": False,
        "score": 0.0,
        "details": "grader did not emit a SCORE_JSON line",
    }


def run_one(task: dict, harness: str, rep: int, report_root: Path) -> dict:
    harness_script = HARNESSES_DIR / f"{harness}.sh"
    if not harness_script.is_file():
        raise TaskError(f"unknown harness {harness!r}: {harness_script} not found")

    run_dir = report_root / task["id"] / harness / f"run{rep}"
    work = run_dir / "work"
    run_dir.mkdir(parents=True, exist_ok=True)

    setup_workdir(task, work)

    prompt = (PROMPT_PREFIX.format(work=work) + task["prompt"].rstrip()
              + PROMPT_SUFFIX.format(work=work))
    prompt_file = run_dir / "prompt.txt"
    prompt_file.write_text(prompt)

    harness_log = run_dir / "harness.log"
    timeout = task["timeout_secs"]
    started = time.time()
    with harness_log.open("w") as log:
        try:
            proc = subprocess.run(
                ["bash", str(harness_script), str(work), str(prompt_file),
                 str(run_dir), str(timeout)],
                stdout=log,
                stderr=subprocess.STDOUT,
                env={**os.environ, "BENCH_TASK_ID": task["id"],
                     "BENCH_TASK_FIELD": task["field"]},
                timeout=timeout + HARNESS_GRACE_SECS,
            )
            harness_rc = proc.returncode
            harness_timed_out = False
        except subprocess.TimeoutExpired:
            harness_rc = 124
            harness_timed_out = True
    wall_secs = round(time.time() - started, 1)

    meta = {
        "harness_rc": harness_rc,
        "harness_completed": harness_rc == 0,
        "harness_timed_out": harness_timed_out,
        "wall_secs": wall_secs,
    }
    (run_dir / "harness_meta.json").write_text(json.dumps(meta, indent=2))

    grade_out = ""
    grade_rc = 2
    if any(work.iterdir()):
        grade_proc = subprocess.run(
            ["bash", str(task["grade"]), str(work)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        grade_out = grade_proc.stdout + grade_proc.stderr
        grade_rc = grade_proc.returncode
    (run_dir / "grade.txt").write_text(grade_out)
    score = parse_score_json(grade_out)

    return {
        "task": task["id"],
        "field": task["field"],
        "harness": harness,
        "rep": rep,
        "passed": bool(score.get("passed")) and harness_rc == 0,
        "score": score.get("score", 0.0) if harness_rc == 0 else 0.0,
        "grade_details": score.get("details", ""),
        "grade_rc": grade_rc,
        **meta,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
    }


def summarize(records: list[dict], report_root: Path) -> None:
    cells: dict[tuple[str, str], list[dict]] = {}
    for rec in records:
        cells.setdefault((rec["task"], rec["harness"]), []).append(rec)

    lines = [
        f"# Benchmark run {report_root.name}",
        "",
        "| task | harness | pass rate | mean score | mean wall | notes |",
        "|---|---|---|---|---|---|",
    ]
    summary: dict[str, dict] = {}
    for (task_id, harness), runs in sorted(cells.items()):
        n = len(runs)
        passes = sum(1 for r in runs if r["passed"])
        mean_score = sum(r["score"] for r in runs) / n
        mean_wall = sum(r["wall_secs"] for r in runs) / n
        harness_fails = sum(1 for r in runs if not r["harness_completed"])
        notes = f"{harness_fails}/{n} harness failures" if harness_fails else ""
        lines.append(
            f"| {task_id} | {harness} | {passes}/{n} | {mean_score:.2f} "
            f"| {mean_wall:.0f}s | {notes} |"
        )
        summary.setdefault(task_id, {})[harness] = {
            "runs": n,
            "passes": passes,
            "pass_rate": passes / n,
            "mean_score": mean_score,
            "mean_wall_secs": mean_wall,
            "harness_failures": harness_fails,
        }
    lines += [
        "",
        "Per-run records: `results.jsonl`. Transcripts: `<task>/<harness>/run<N>/`.",
        "Classify failure modes by reading transcripts before trusting a 0.",
        "",
    ]
    (report_root / "summary.md").write_text("\n".join(lines))
    (report_root / "summary.json").write_text(json.dumps(summary, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tasks", nargs="+", metavar="TASK",
                    help="task paths (e.g. bugfix/py-cache-invalidation), ids, or 'all'")
    ap.add_argument("--harnesses", type=str, default="peko",
                    help="comma-separated harness names (default: peko)")
    ap.add_argument("--reps", type=int, default=1,
                    help="repetitions per task × harness cell (default: 1; use ≥3 for real runs)")
    ap.add_argument("--tag", type=str, default="",
                    help="label appended to the report directory name")
    ap.add_argument("--list", action="store_true", help="list tasks and exit")
    args = ap.parse_args()

    if args.list:
        list_tasks()
        return 0
    if not args.tasks:
        ap.error("--tasks is required (or use --list)")
    if args.reps < 1:
        ap.error("--reps must be >= 1")

    tasks = discover_tasks(args.tasks)
    harnesses = [h.strip() for h in args.harnesses.split(",") if h.strip()]
    if not harnesses:
        ap.error("--harnesses resolved to an empty list")

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_name = stamp + (f"-{args.tag}" if args.tag else "")
    report_root = REPORTS_DIR / report_name
    report_root.mkdir(parents=True, exist_ok=True)

    print(f"report dir: {report_root.relative_to(REPO_ROOT)}")
    print(f"matrix: {len(tasks)} tasks × {len(harnesses)} harnesses × "
          f"{args.reps} reps = {len(tasks) * len(harnesses) * args.reps} runs")

    records: list[dict] = []
    results_path = report_root / "results.jsonl"
    total = len(tasks) * len(harnesses) * args.reps
    done = 0
    for task in tasks:
        for harness in harnesses:
            for rep in range(1, args.reps + 1):
                done += 1
                print(f"[{done}/{total}] {task['id']} × {harness} rep {rep} …",
                      flush=True)
                try:
                    rec = run_one(task, harness, rep, report_root)
                except Exception as exc:  # keep the matrix going on a bad cell
                    rec = {
                        "task": task["id"], "field": task["field"],
                        "harness": harness, "rep": rep,
                        "passed": False, "score": 0.0,
                        "grade_details": "", "grade_rc": 2,
                        "harness_rc": -1, "harness_completed": False,
                        "harness_timed_out": False, "wall_secs": 0.0,
                        "run_dir": "", "runner_error": str(exc),
                    }
                records.append(rec)
                with results_path.open("a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                status = "PASS" if rec["passed"] else (
                    "HARNESS-FAIL" if not rec["harness_completed"] else "fail")
                print(f"         → {status} score={rec['score']:.2f} "
                      f"wall={rec['wall_secs']:.0f}s {rec['grade_details']}",
                      flush=True)

    summarize(records, report_root)
    passed = sum(1 for r in records if r["passed"])
    print(f"\ndone: {passed}/{len(records)} runs passed — "
          f"see {report_root.relative_to(REPO_ROOT)}/summary.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
