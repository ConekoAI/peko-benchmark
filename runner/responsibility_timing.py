"""Native Peko cron completion evidence, independent of model claims and grading."""
import json
from pathlib import Path

from responsibility_audit import timestamp


def native_cron_timing(run_dir: Path, start: float, end: float):
    snapshot = run_dir / 'topology-post-watch.json'
    if not snapshot.exists():
        return {'version': 1, 'measured': False, 'reason': 'no Peko post-watch schedule snapshot'}
    schedule = json.loads(snapshot.read_text()).get('schedule', {})
    # OpenClaw snapshots use a different native contract; do not infer parity.
    if not isinstance(schedule, dict) or 'runs' not in schedule:
        return {'version': 1, 'measured': False, 'reason': 'native Peko cron evidence unavailable'}
    jobs = {j['id']: j for j in schedule.get('jobs', [])}
    events = {}
    for path in (run_dir / 'runtime-traces/data/runtime/audit').glob('*.jsonl'):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get('event_type') != 'cron.result':
                continue
            detail = row.get('details', {})
            required = ('scheduled_at', 'finished_at', 'next_run_at', 'skipped_interval_slots', 'duration_ms')
            if not all(k in detail for k in required):
                continue
            if detail.get('status') == 'running' or detail.get('finished_at') is None:
                continue
            finish = timestamp(detail['finished_at'])
            began = finish - detail['duration_ms'] / 1000
            if finish < start or began > end:
                continue
            job = jobs.get(detail.get('job_id'), {})
            interval = job.get('schedule', {}).get('every_ms')
            period = interval / 1000 if interval else None
            events[detail['run_id']] = {
                'run_id': detail['run_id'], 'job_id': detail['job_id'], 'job_name': detail.get('job_name'),
                'status': detail['status'], 'duration_secs': detail['duration_ms'] / 1000,
                'nominal_interval_secs': period, 'scheduled_at': detail['scheduled_at'],
                'finished_at': detail['finished_at'], 'next_run_at': detail['next_run_at'],
                'late_admission_secs': round(began - timestamp(detail['scheduled_at']), 3),
                'skipped_interval_slots': detail['skipped_interval_slots'],
                'turn_exceeded_interval': detail['duration_ms'] > interval if interval else None,
            }
    censored = [r['id'] for r in schedule.get('runs', []) if r.get('finished_at') is None
                and timestamp(r['started_at']) <= end and r.get('job_id') in jobs]
    if not events:
        return {'version': 1, 'measured': False, 'reason': 'no new native completion timing fields',
                'open_runs_at_snapshot': censored}
    runs = sorted(events.values(), key=lambda r: r['finished_at'])
    workers = [r for r in runs if r['job_name'] == 'responsibility-monitor']
    return {'version': 1, 'measured': True, 'runs': runs, 'open_runs_at_snapshot': censored,
            'worker_completed_runs': len(workers),
            'worker_turns_exceeding_interval': sum(r['turn_exceeded_interval'] is True for r in workers),
            'worker_max_turn_secs': max((r['duration_secs'] for r in workers), default=None),
            'worker_skipped_interval_slots': sum(r['skipped_interval_slots'] or 0 for r in workers),
            'limitation': 'Completed native run audits only; open/interrupted runs are not zero-duration successes. '
                          'Skipped slots include late admission and execution, not necessarily missed observations.'}
