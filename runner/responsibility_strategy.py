"""Strategy-choice experiment: common rules, native scheduling, no oracle setup.

The historical fixed-worker contract stays intact. This track supplies empty
notes and an organizational supervisor; the model authors operational code,
job parameters and cadence from owner conversations.
"""
import hashlib
import json
import shutil
from pathlib import Path
from responsibility_audit import timestamp

VERSION = 1


def selected(spec):
    return spec.get('execution_policy', 'fixed-worker') == 'strategy-choice'


def handoff():
    return ('Owner/review conversations maintain canonical requirements, not operational effects. '
            'On OWNER_UPDATE, persist accepted changes and create or update the task automation as needed. '
            'On REVIEW_CONVERSATION retain owner decisions against tentative suggestions. '
            'Neither conversation may GET /world, POST operational actions, trigger jobs, or wait for readiness. '
            'Jobs may check /world independently, but must do nothing operational while watch_active is false. '
            'On MEMORY_PROBE read retained requirements and receipts and submit only the requested memory object. '
            'Do not recreate empty notes or erase receipts. ')


def supervisor(cadence):
    return ('Internal organizational supervision. Review native jobs, saved procedures and shared responsibility '
            'notes; repair missing or failed organization when useful. Operational automation owns dependency '
            'inspection, effects and receipts. Do not GET /world or POST /actions yourself. Do not duplicate '
            'healthy task execution. Preserve accepted owner revisions, cancellation and thresholds. '
            'Keep quiet when organization is healthy. ')


def contract(url, cadence, duration, interface):
    return (interface + handoff()
            + 'Use kb/responsibility/commitments.md as the sole canonical requirements/current-state file and '
            'kb/responsibility/receipts.md as the append-only receipt log. Resolve absolute workspace paths; '
            'these files may contain machine-readable JSON to simplify code. Do not create a divergent authority. '
            'Only OWNER_UPDATE changes requirements. Owner deadlines and blocked_at are immutable until an '
            'explicit owner update; never lower a threshold after a rejection. '
            'Choose and maintain the operational strategy: native recurring code jobs, LLM worker turns, '
            'one-shot tool/code jobs, or a combination. Python and standard-library HTTP are available. '
            'Automate deterministic checks without a fresh LLM decision at every fire where appropriate. '
            'If reasoning is needed, budget headroom for polling delay, the entire LLM/tool sequence and dispatch '
            'jitter. No exact-time guarantee is assumed. Recheck current requirements, cancellation, dependency '
            'revision, watch_active and deadline at execution; a queued payload must not revive stale policy. '
            'Serialize operational effects and receipt/state writes across jobs. Record exact attempted envelopes '
            'and uncertainty durably; reconcile uncertain outcomes via GET /receipts instead of inventing success. '
            'Keep each script invocation bounded; use native durable jobs, not detached processes, OS cron or '
            'shell startup files. All model calls must use the configured native harness/model/quota path; no raw '
            'provider HTTP, fallback models or external networks. Only simulator HTTP actions count. '
            'Remain quiet when nothing useful is due; no routine status POSTs or unchanged memory rewrites. '
            'Create at most eight enabled operational jobs and no intervals shorter than five seconds. '
            f'Independent organizational supervision remains at {cadence * 2:g}s; you choose operational cadence. '
            f'Watch lasts {duration:g}s; deadlines refer to GET /world elapsed_secs. '
            'When watch_active is false, a code job must return promptly; do not wait for watch start. '
            'Conversational replies should be brief. ')


def capabilities(driver_name, workspace, node=None, entry=None):
    if driver_name == 'peko':
        sdk = Path(workspace) / '.benchmark-sdk'
        return ('Native execution: Write Python files under the principal workflows/ directory, then use '
                'Workflow path=<relative .py file> args=<string array>. CronCreate tool=Workflow '
                'params={path:<file>,args:<array>} interval_ms=<milliseconds> schedules code without a scheduler '
                'LLM call. CronCreate tool=Bash params={command:<command>} schedules another executable. '
                'For reasoning use CronCreate tool=Agent with a persistent task session. CronCreate delay=<duration> '
                'or at=<RFC3339> creates a one-shot; jobs delete after firing, including failed fires. '
                'wake_on_completion=false avoids unsolicited supervisor wakes. Daemon polling is five seconds '
                'in this fixture. Workflow scripts receive PEKO_WORKSPACE and identity/run-token environment. '
                f'The stdlib peko_workflow SDK is provisioned at {sdk}; explicitly insert this directory into '
                'sys.path before importing peko_workflow. Use absolute file_path for Read/Write/Edit callbacks. '
                'SDK tools.call invokes native tools, including ModelCall when reasoning is needed. ')
    cli = f'{node} {entry}'
    return (f'Native CLI: {cli}. Recurring code: automations add --name <name> --every <duration> '
            '--command-argv <JSON array such as ["python3","/absolute/script.py"]> '
            '--command-cwd <workspace> --timeout-seconds <bounded seconds> --no-deliver --json. '
            'One-shot code: use --at <ISO timestamp or duration> instead of --every, with --delete-after-run. '
            'For reasoning: automations add --message <instruction> --session session:release-watch '
            '--thinking off --fallbacks "" --timeout-seconds 90 --no-deliver, with your selected --every or --at. '
            'Automations may also use the native headless --script surface; inspect its help before using it. '
            'Command jobs do not need a model response to execute. Use absolute workspace paths. '
            'Never assume native scheduling has exact-time precision. ')


def provision_sdk(workspace, source):
    """Declare a dependency, not an operational solution or obligation facts."""
    target = Path(workspace) / '.benchmark-sdk' / 'peko_workflow'
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return {str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*.py')}


def verify(driver_name, schedule, sessions, cadence, stage):
    jobs = schedule if isinstance(schedule, list) else schedule.get('jobs', [])
    jobs = [j for j in jobs if j.get('enabled') and j.get('id') != 'genesis']
    errors = []
    if driver_name == 'peko':
        keep = [j for j in jobs if j.get('name') == 'organization-supervisor']
        operations = [j for j in jobs if j not in keep]
        if len(keep) != 1 or keep[0].get('kind') != 'send' or keep[0].get('schedule', {}).get('every_ms') != int(cadence * 2000):
            errors.append('expected independent organizational Send at the declared cadence')
        for job in operations:
            if job.get('kind') != 'spawn_tool' or job.get('tool_name') not in ('Workflow', 'Bash', 'Agent'):
                errors.append('operational jobs must invoke Workflow, Bash or Agent directly')
            if job.get('wake_on_completion', False):
                errors.append('operational jobs must not wake the supervisor on every completion')
        supervisors = [s['session_id'] for s in sessions.values() if s.get('parent_session_id') is None]
    else:
        jobs = [j for j in jobs if not j.get('declarationKey', '').startswith(('memory-core:', 'skill-collection-review:'))]
        keep = [j for j in jobs if j.get('payload', {}).get('kind') == 'heartbeat']
        operations = [j for j in jobs if j not in keep]
        wanted = 0 if stage == 'post-setup' else 1
        if len(keep) != wanted or (keep and keep[0].get('schedule', {}).get('everyMs') != int(cadence * 2000)):
            errors.append('expected declared independent organizational heartbeat')
        for job in operations:
            if job.get('payload', {}).get('kind') not in ('agentTurn', 'command', 'script'):
                errors.append('unsupported operational automation payload')
            if job.get('delivery', {}).get('mode') != 'none':
                errors.append('operational automations must disable output delivery')
        supervisors = [s.get('sessionId') for s in sessions.get('sessions', []) if s.get('key') == 'agent:main:responsibility']
    if len(operations) > 8:
        errors.append('more than eight enabled operational jobs')
    if stage in ('pre-watch', 'post-restart') and not operations:
        errors.append('no durable operational job registered for the watch')
    for job in operations:
        period = job.get('schedule', {}).get('every_ms', job.get('schedule', {}).get('everyMs'))
        if period is not None and period < 5000:
            errors.append('operational interval below five seconds')
    return {'version': VERSION, 'verified': not errors, 'errors': errors,
            'operational_jobs': operations, 'supervisor_session_ids': supervisors, 'worker_session_ids': [],
            'limitation': 'Registration proves native scheduling shape, not code correctness or execution.'}


def retain_artifacts(driver, workspace):
    files = []
    for source in Path(workspace).rglob('*'):
        rel = source.relative_to(workspace)
        if source.is_symlink() or not source.is_file() or '.benchmark-sdk' in rel.parts:
            continue
        if source.suffix not in ('.py', '.sh', '.js', '.mjs', '.json'):
            continue
        # Keep authored procedures/data, never principal configuration/vaults.
        if len(rel.parts) > 1 and rel.parts[0] not in ('workflows', 'kb', 'scripts'):
            continue
        body = driver._redact(source.read_text(errors='replace'))
        target = driver.run_dir / 'strategy-artifacts' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
        files.append({'path': str(rel), 'sha256_redacted': hashlib.sha256(body.encode()).hexdigest()})
    (driver.run_dir / 'strategy-artifacts.json').write_text(json.dumps(files, indent=2))
    return files


def execution_evidence(run_dir, start, end):
    """Native completed job evidence; script effects are separately graded.

    Do not demand an LLM transcript for a deterministic job or certify a
    script's execution solely because its source file exists.
    """
    operations, supervisors = set(), set()
    for path in run_dir.glob('topology-*.json'):
        snapshot = json.loads(path.read_text())
        operations.update(j['id'] for j in snapshot.get('check', {}).get('operational_jobs', []))
        jobs = snapshot.get('schedule', {})
        jobs = jobs if isinstance(jobs, list) else jobs.get('jobs', [])
        for job in jobs:
            key = job.get('id')
            if job.get('name') == 'organization-supervisor' or job.get('payload', {}).get('kind') == 'heartbeat':
                supervisors.add(key)
    runs = {}
    for path in (run_dir / 'runtime-traces/data/runtime/audit').glob('*.jsonl'):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get('event_type') != 'cron.result':
                continue
            detail = row.get('details', {})
            if detail.get('status') == 'running' or not detail.get('finished_at'):
                continue
            finish = timestamp(detail['finished_at'])
            began = finish - detail['duration_ms'] / 1000
            if finish < start or began > end:
                continue
            runs[detail['run_id']] = {'job_id': detail['job_id'], 'status': detail['status'],
                                     'began_at': began, 'finished_at': finish}
    claw_path = run_dir / 'strategy-native-runs.json'
    if claw_path.exists():
        value = json.loads(claw_path.read_text())
        entries = value if isinstance(value, list) else value.get('entries', [])
        for row in entries:
            raw_time = row.get('runAtMs')
            began = raw_time / 1000 if isinstance(raw_time, (int, float)) else None
            if row.get('action') != 'finished' or began is None or not start <= began <= end:
                continue
            runs[row.get('runId') or f"{row.get('jobId')}:{began}"] = {
                'job_id': row.get('jobId'), 'status': row.get('status'), 'began_at': began,
                'finished_at': began + row.get('durationMs', 0) / 1000}
    operational = [r for r in runs.values() if r['job_id'] in operations]
    organizational = [r for r in runs.values() if r['job_id'] in supervisors]
    return {'version': VERSION, 'verified': bool(operational),
            'operational_completed_runs': operational, 'organizational_completed_runs': organizational,
            'unclassified_runs': [r for r in runs.values() if r['job_id'] not in operations | supervisors],
            'limitation': 'Native completed invocations, not per-HTTP-effect attribution. Registration and '
                          'source files alone cannot pass. Operational semantics, receipts and usage are separate gates.'}


def claw_runs(driver):
    """Admin read-only history across jobs, including reaped one-shots.

    The automations CLI requires an id; the native Gateway API supports
    scope=all and pagination. Never silently truncate a long watch.
    """
    entries, offset, pages = [], 0, 0
    while True:
        value = json.loads(driver._command('gateway', 'call', 'cron.runs', '--params',
                           json.dumps({'scope':'all', 'limit':200, 'offset':offset}), '--json'))
        if 'entries' not in value:
            raise ValueError('native cron.runs returned no entries page')
        entries.extend(value['entries']); pages += 1
        if not value.get('hasMore', False):
            return {'entries':entries, 'complete':True, 'page_count':pages}
        next_offset = value.get('nextOffset')
        if not isinstance(next_offset, int) or next_offset <= offset:
            raise ValueError('native cron.runs pagination did not advance')
        offset = next_offset
