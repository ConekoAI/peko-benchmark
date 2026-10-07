"""Declared controller-authored empty organization for execution-only trials.

Formation is assessed separately. These fixtures contain no commitment facts,
model transcript, receipts, or simulator oracle values.
"""
from __future__ import annotations
import datetime as dt
import json
import time
import uuid
from pathlib import Path
from responsibility_topology import task_paths, handoff_prompt, supervisor_prompt


def empty_notes(workspace: Path, worker_prompt: str):
    folder = workspace / 'kb/responsibility'; folder.mkdir(parents=True, exist_ok=True)
    (folder / 'commitments.md').write_text('# Shared requirements\n\nNo commitments received yet.\n')
    (folder / 'receipts.md').write_text('# Action receipts (append-only)\n\n')
    (workspace / 'RESPONSIBILITY.md').write_text(task_paths() + handoff_prompt() + '\n' + worker_prompt)


def prepare_peko(driver, worker_prompt):
    driver._stop_owned_daemon()
    home = Path(driver.temp.name) / '.peko'
    root = home / 'data/principals' / driver.principal
    workspace = home / 'principals' / driver.principal
    empty_notes(workspace, worker_prompt)
    roles = workspace / 'roles'; roles.mkdir(exist_ok=True)
    (roles / 'release-watch.md').write_text('---\nname: release-watch\ndescription: Periodic release responsibility worker\n---\n' + worker_prompt)
    indices = list(root.rglob('sessions.json'))
    schedules = list(root.rglob('cron/schedule.toml'))
    if len(indices) != 1 or len(schedules) != 1:
        raise ValueError('prepared topology requires unique native index and schedule')
    sessions = json.loads(indices[0].read_text())
    trunks = [s for s in sessions.values() if s.get('parent_session_id') is None]
    if len(trunks) != 1:
        raise ValueError('prepared topology requires one native trunk')
    trunk = trunks[0]; sid = str(uuid.uuid4()); now = int(time.time() * 1000)
    child = dict(trunk, session_id=sid, parent_session_id=trunk['session_id'], slug='release-watch',
                 peer_type='principal', peer_id='prepared_worker', trigger='spawn', title=None,
                 created_at=now, updated_at=now, transcript_file=sid + '.jsonl')
    for key in ('message_count', 'turn_count', 'last_total_tokens', 'total_input_tokens', 'total_output_tokens',
                'pruned_pages', 'compaction_count', 'consecutive_auto_compactions', 'consecutive_compaction_failures'):
        child[key] = 0
    sessions[sid] = child
    indices[0].write_text(json.dumps(sessions, indent=2))
    indices[0].with_name(sid + '.jsonl').write_text('')
    schedule = json.loads(schedules[0].read_text())
    identity = next(j['principal_id'] for j in schedule['jobs'])
    cadence = driver.sim.spec['cadence_secs']
    stamp = dt.datetime.now(dt.timezone.utc)
    def job(name, multiple, action):
        return {'id': 'prepared-' + name, 'name': name, 'principal_id': identity,
                'schedule': {'kind': 'every', 'every_ms': int(cadence * multiple * 1000)},
                'created_at': stamp.isoformat(), 'next_run': (stamp + dt.timedelta(seconds=3600)).isoformat(),
                'delete_after_run': False, 'enabled': True, 'run_count': 0, 'consecutive_failures': 0,
                'origin_session': trunk['session_id'], **action}
    schedule['jobs'] = [job('organization-supervisor', 2, {'kind': 'send', 'message': supervisor_prompt(cadence)}),
                        job('responsibility-monitor', 1, {'kind': 'spawn_tool', 'tool_name': 'Agent',
                            'tool_params': {'action': 'new', 'path': '/release-watch', 'role': 'release-watch', 'prompt': worker_prompt},
                            'wake_on_completion': False, 'timeout_secs': 90})]
    schedules[0].write_text(json.dumps(schedule, indent=2))
    driver._command('daemon', 'start', '--interval', '5'); driver._ready()
    driver.metadata['formation'] = 'controller_prepared_empty_native_topology'


def arm_peko(driver):
    driver._stop_owned_daemon()
    root = Path(driver.temp.name) / '.peko/data/principals' / driver.principal
    path = next(root.rglob('cron/schedule.toml')); schedule = json.loads(path.read_text())
    now = dt.datetime.now(dt.timezone.utc)
    for job in schedule['jobs']:
        offset = 20 if job['name'] == 'responsibility-monitor' else driver.sim.spec['cadence_secs'] * 2
        job['next_run'] = (now + dt.timedelta(seconds=offset)).isoformat()
    path.write_text(json.dumps(schedule, indent=2))
    driver._command('daemon', 'start', '--interval', '5'); driver._ready()


def prepare_claw(driver, worker_prompt):
    empty_notes(driver.workspace, worker_prompt)
    (driver.workspace / 'BOOTSTRAP.md').unlink(missing_ok=True)
    (driver.workspace / 'IDENTITY.md').write_text('# Responsibility Bench\nConcise release coordinator.\n')
    (driver.workspace / 'USER.md').write_text('# User\nThe benchmark owner supplies requirements in chat.\n')
    (driver.workspace / 'SOUL.md').write_text('# Purpose\nOrganize responsibility workers and preserve shared requirements.\n' + handoff_prompt())
    driver._command('agents', 'set-identity', '--agent', 'main', '--workspace', str(driver.workspace),
                    '--name', 'Responsibility Bench', '--theme', 'Concise release coordinator', '--emoji', '📋')
    driver._command('automations', 'add', '--name', 'responsibility-monitor',
                    '--every', f"{driver.sim.spec['cadence_secs']:g}s", '--session', 'session:release-watch',
                    '--thinking', 'off', '--timeout-seconds', '90', '--no-deliver', '--fallbacks', '',
                    '--message', worker_prompt)
    set_claw_due_times(driver)
    driver.metadata['formation'] = 'controller_prepared_empty_native_topology'


def set_claw_due_times(driver, armed=False):
    # Only the worker is client-owned. Native heartbeat jobs must be changed
    # through configuration, not cron.update or storage mutation.
    if armed:
        driver._command('config', 'set', 'agents.defaults.heartbeat.every',
                        f"{driver.sim.spec['cadence_secs'] * 2:g}s")
        driver._stop_gateway()
        driver._start_gateway()
    schedule = json.loads(driver._command('automations', 'list', '--all', '--json'))
    jobs = schedule if isinstance(schedule, list) else schedule.get('jobs', [])
    monitors = [j for j in jobs if j.get('name') == 'responsibility-monitor']
    if len(monitors) != 1:
        raise ValueError('prepared clock requires one client-owned worker')
    offset = 20_000 if armed else 3_600_000
    params = {'id': monitors[0]['id'], 'patch': {'schedule': {'kind': 'every',
              'everyMs': int(driver.sim.spec['cadence_secs'] * 1000), 'anchorMs': int(time.time()*1000) + offset}}}
    driver._command('gateway', 'call', 'cron.update', '--params', json.dumps(params), '--json')
