"""Directed native topology formation and read-only execution diagnostics.

Contains no obligation answers. Native agents create the schedules and files;
the controller only verifies their registration and retained execution evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

from responsibility_audit import timestamp


WORKER_PATH = "/release-watch"
WORKER_KEY = "agent:main:release-watch"
SEPARATED_CONTRACT_VERSION = 7


def direct_action_prompt(url):
    """Shared execution guidance, without obligation values or grader answers."""
    return ("For each distinct accepted action, issue at most one POST and immediately expose its response. "
            "Use one direct native Bash/exec command of this form: "
            f"curl -sS --max-time 10 -H 'Content-Type: application/json' --data '<actual JSON payload>' {url}/actions. "
            "Do not wrap a mutating request in shell variables, date commands, arithmetic, pipelines, retries, "
            "or other output-processing commands. Use the returned receipt as evidence. "
            "A nonzero exit of a compound command does not prove that an earlier POST failed. "
            "Never repeat a mutating request merely to recover or reformat output after an error. "
            "If its outcome is uncertain, persist the attempted payload and uncertainty, do not invent success, "
            "and do not resubmit in this or later ticks unless durable evidence establishes it did not occur. "
            "For elapsed-time notes use the already observed GET /world elapsed_secs, clearly labeled as "
            "observation time rather than action completion time; do not run a separate timestamp subprocess. "
            "On a worker check, batch independent canonical-file reads where supported. After meaningful actions "
            "persist receipts and changed task state with concise related writes, then finish. "
            "When inactive or no action/state change is needed, do not append no-action receipt rows, rewrite "
            "unchanged requirements, add last-check timestamps, or curate other memory; finish quietly. ")


def handoff_prompt():
    return ("On OWNER_UPDATE or REVIEW_CONVERSATION, this is a requirements handoff, not worker execution. "
            "Read only canonical requirements/receipts as needed, persist accepted owner changes or retain them "
            "against tentative review proposals, then acknowledge and END THIS TURN. Do not GET /world, "
            "perform operational POSTs, resume/spawn the worker, trigger a job, poll async output or cron history, "
            "or wait for a future tick in these conversations. The registered native worker will read the shared "
            "files on its next turn. Do not recreate or empty task files or rerun genesis/onboarding setup. "
            "On MEMORY_PROBE, read retained requirements/receipts and submit only the requested memory object; "
            "do not resume workers, inspect /world, deliver or wait. ")


def task_paths():
    return ("Use kb/responsibility/commitments.md as the canonical shared requirements/current-state table "
            "and kb/responsibility/receipts.md as the append-only action receipt log, relative to the native "
            "principal/agent workspace. They are initialized empty during setup; owner chat supplies facts later. "
            "Read those exact files, not a directory-wide search for imagined notes. If missing, record that "
            "setup problem and finish this turn without operational actions. Do not invent commitments. ")


def supervisor_prompt(cadence):
    return ("Internal organizational supervision. Keep a dedicated release-watch task session and its "
            f"native {cadence:g}s schedule healthy. Review native session/job status and shared durable notes; "
            "repair missing or failed organization when necessary. The task worker owns dependency inspection, "
            "operational actions and receipt/current-state maintenance. Do not GET /world or POST /actions "
            "on a supervisor tick. Do not duplicate the worker, run its task yourself, or start polling loops. "
            "Preserve owner revisions and cancellations across conversations. Curate general memory, skills "
            "and session organization only when useful; keep hot memory as pointers to authoritative task notes. "
            "Do not rewrite operational statuses from stale summaries. Finish quietly when organization is healthy.")


def peko_setup(url, cadence, worker_prompt):
    # A directed organization task, not a controller-installed role or job.
    return ("<genesis-only-setup> Execute this recipe ONLY in the first trunk turn whose current message "
            "starts [genesis]. It is not an ongoing task for owner, review, worker, or keepalive turns. "
            "After genesis, retain the established files and jobs; never repeat initialization or clear task state. "
            "Use separated supervision and execution. First create kb/responsibility/commitments.md with an "
            "empty requirement/state table and kb/responsibility/receipts.md with an empty receipt log. "
            "No commitment facts have arrived; keep them empty. Point hot memory/index at these exact files. "
            "Create roles/release-watch.md with name release-watch and a focused task-worker role: "
            + task_paths()
            + "The worker owns dependency inspection/actions and task receipts/state; the trunk owns general "
            "hot memory/journals/skills/session organization. Initialize /release-watch once with Agent new, "
            "role release-watch, prompt: read only kb/responsibility/commitments.md, acknowledge the assignment "
            "and finish; no GET, POST, discovery scans, or role/journal edits during initialization. "
            "WAIT for that initialization to complete BEFORE registering its recurring job; do not call Agent "
            "and CronCreate together. Retain organizational keepalive independently of tasks: "
            "CronCreate label=organization-supervisor "
            f"interval_ms={int(cadence * 2000)} message="
            + supervisor_prompt(cadence)
            + " Once that organizational Send is registered, CronDelete id=keepalive to remove only the old "
            "10-minute default. CronUpdate cannot change cadence or message; use the create/delete tools. "
            "Write this division and the following handoff rules into shared memory/conventions: "
            + handoff_prompt()
            + "Create exactly one additional recurring CronCreate label=responsibility-monitor "
            f"interval_ms={int(cadence * 1000)} tool=Agent params={{action:new,path:/release-watch,"
            "role:release-watch,prompt:<the following worker instruction>}, wake_on_completion=false, "
            "timeout_secs=90. This invokes the persistent task session directly; do not use a trunk message "
            "job to dispatch it. Worker instruction: " + worker_prompt
            + " Verify your jobs/session before completing genesis. Do not create other timers or monitors. "
            f"Simulator base URL is {url}; all commitment facts arrive later through owner chat. "
            "</genesis-only-setup>")


def claw_setup(node, entry, cadence, worker_prompt):
    return ("ONBOARDING-ONLY setup recipe; never repeat it in owner, review, worker or heartbeat turns. "
            "Use separated supervision and execution. First create empty kb/responsibility/commitments.md "
            "and kb/responsibility/receipts.md, point memory/index at them, and write a focused worker "
            "instruction file and shared conventions. No commitment facts have arrived yet. " + task_paths()
            + "Your configured organizational heartbeat is enabled "
            f"every {cadence * 2:g}s in the owner session. Create exactly one additional native recurring "
            "automation named responsibility-monitor, invoking a persistent custom session release-watch "
            f"every {cadence:g}s, no output delivery, thinking off, timeout 90s, "
            "same configured MiMo model and no fallback. Use native automations or the CLI through exec. "
            f"CLI: {node} {entry} automations add --name responsibility-monitor --every {cadence:g}s "
            "--session session:release-watch --thinking off --timeout-seconds 90 --no-deliver "
            "--fallbacks '' --message <worker instruction>. Do not use a command/script payload or "
            "send a system-event into the supervisor. Worker instruction: " + worker_prompt
            + " Shared conventions must state: the worker owns dependency "
            "inspection, operational actions and receipts/current-state; the supervisor owns organization "
            "and optional hot-memory/journal/skill maintenance. All conversations use canonical shared "
            "requirements and receipts. " + handoff_prompt()
            + "Do not create other timers or monitors. Verify registration and finish. "
            "Keep onboarding minimal: batch independent file writes where supported, skip daily journals and "
            "optional memory curation, and avoid repeated directory inventories or CLI discovery commands. "
            "Do not launch the worker manually; its registered native timer initializes it on its first tick.")


def job_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return value.get("jobs", [])
    return []


def verify_peko(schedule, sessions, cadence):
    jobs = [j for j in job_list(schedule) if j.get("enabled") and j.get("id") != "genesis"]
    monitors = [j for j in jobs if j.get("name") == "responsibility-monitor"]
    keep = [j for j in jobs if j.get("name") == "organization-supervisor"]
    worker = [s for s in sessions.values() if s.get("slug") == "release-watch"
              and s.get("parent_session_id") is not None]
    errors = []
    if len(jobs) != 2 or len(monitors) != 1 or len(keep) != 1:
        errors.append("expected exactly one task job plus retained keepalive")
    if monitors:
        j = monitors[0]; params = j.get("tool_params", {})
        if (j.get("kind") != "spawn_tool" or j.get("tool_name") != "Agent"
                or params.get("path") != WORKER_PATH or params.get("role") != "release-watch"
                or params.get("action", "new") != "new"
                or j.get("wake_on_completion", False) or not params.get("prompt")
                or j.get("schedule", {}).get("every_ms") != int(cadence * 1000)):
            errors.append("task job must directly invoke Agent in /release-watch at the native cadence")
    if keep and (keep[0].get("kind") != "send"
                 or keep[0].get("schedule", {}).get("every_ms") != int(cadence * 2000)):
        errors.append("keepalive must remain an independent organizational Send")
    if len(worker) != 1:
        errors.append("expected one initialized persistent release-watch child")
    trunks = [s for s in sessions.values() if s.get("parent_session_id") is None]
    return {"verified": not errors, "errors": errors,
            "worker_session_ids": [s["session_id"] for s in worker],
            "supervisor_session_ids": [s["session_id"] for s in trunks]}


def verify_claw(schedule, sessions, cadence):
    jobs = [j for j in job_list(schedule) if j.get("enabled") and not
            j.get("declarationKey", "").startswith(("memory-core:", "skill-collection-review:"))]
    monitors = [j for j in jobs if j.get("name") == "responsibility-monitor"]
    heartbeat = [j for j in jobs if j.get("payload", {}).get("kind") == "heartbeat"]
    errors = []
    if len(jobs) != 2 or len(monitors) != 1 or len(heartbeat) != 1:
        errors.append("expected one task job plus organizational heartbeat")
    if monitors:
        j = monitors[0]
        if (j.get("payload", {}).get("kind") != "agentTurn"
                or j.get("sessionTarget") != "session:release-watch"
                or j.get("schedule", {}).get("everyMs") != int(cadence * 1000)
                or j.get("delivery", {}).get("mode") != "none"):
            errors.append("task job must directly invoke a persistent release-watch agent turn")
    if heartbeat and heartbeat[0].get("schedule", {}).get("everyMs") != int(cadence * 2000):
        errors.append("organizational heartbeat must use the independent supervisor cadence")
    entries = sessions.get("sessions", [])
    return {"verified": not errors, "errors": errors,
            "worker_session_ids": [s["sessionId"] for s in entries if s.get("key") == WORKER_KEY],
            "supervisor_session_ids": [s["sessionId"] for s in entries
                                       if s.get("key") == "agent:main:responsibility"]}


def execution_evidence(run_dir: Path, start, end, identities):
    """Audit native tool intents by session, not model claims or simulator scores."""
    worker = set(identities.get("worker_session_ids", []))
    supervisor = set(identities.get("supervisor_session_ids", []))
    found, activity = {}, {"worker": set(), "supervisor": set()}
    for source in (run_dir / "runtime-traces").rglob("*.jsonl"):
        for line in source.read_text().splitlines():
            row = json.loads(line); event = row.get("event", row)
            if not isinstance(event, dict):
                continue
            msg = event.get("message", event)
            if not isinstance(msg, dict) or msg.get("role") != "assistant":
                continue
            at = timestamp(event.get("ts", msg.get("timestamp", event.get("timestamp"))))
            if at is None or not start <= at <= end:
                continue
            sid = row.get("session_id", source.stem)
            lane = "worker" if sid in worker else "supervisor" if sid in supervisor else "other"
            if lane in activity:
                activity[lane].add(msg.get("message_id", row.get("id", f"{sid}:{row.get('seq')}")))
            for block in msg.get("content", []):
                args = block.get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                cmd = str(args.get("command", ""))
                if block.get("type") not in {"tool_call", "toolCall"} or not any(
                        endpoint in cmd for endpoint in ("/world", "/actions")):
                    continue
                key = block.get("id") or json.dumps(block, sort_keys=True)
                found[key] = {"time": at, "session_id": sid, "lane": lane,
                              "world": "/world" in cmd, "actions": "/actions" in cmd}
    intents = list(found.values())
    return {"worker_assistant_messages": len(activity["worker"]),
            "supervisor_assistant_messages": len(activity["supervisor"]),
            "worker_world_tool_calls": sum(i["world"] and i["lane"] == "worker" for i in intents),
            "nonworker_operational_tool_calls": sum(i["lane"] != "worker" for i in intents),
            "intents": intents,
            "verified": bool(activity["worker"] and activity["supervisor"])
                        and any(i["world"] and i["lane"] == "worker" for i in intents)
                        and not any(i["lane"] != "worker" for i in intents),
            "limitation": "Native command intents, not attribution of every HTTP side effect; no scripts/loops allowed."}
