"""Versioned evidence diagnostics; no answers are exposed to native agents."""
from __future__ import annotations
import json
import re
from pathlib import Path

DIAGNOSTICS_VERSION = 1


def observed_preconditions(spec, rows):
    """Distinguish readiness at POST time from readiness actually observed.

    Older ledgers omit snapshots; their world_version indexes the recorded
    changes. Single-worker fixture only: reads lack caller identity.
    """
    world = {o['project']: {'ready': False, 'revision': o['revision']} for o in spec['obligations']}
    snapshots = {0: json.loads(json.dumps(world))}
    version = 0
    for row in rows:
        if row['kind'] == 'world_change':
            change = row['change']; world[change['project']] = {k: change[k] for k in ('ready', 'revision')}
            version += 1; snapshots[version] = json.loads(json.dumps(world))
    expected = {o['project']: o for o in spec['obligations']}
    last = None
    evidence = []
    for row in rows:
        if row['kind'] == 'read':
            last = row
        if row['kind'] != 'action' or row['action'].get('kind') not in ('send_release', 'request_input'):
            continue
        action = row['action']; obligation = expected.get(action.get('project'))
        active = bool(last and last['phase'] == 'watch' and last.get('elapsed_secs') is not None)
        state = (last.get('snapshot', {}).get('dependencies') or snapshots.get(last.get('world_version'), {})) if last else {}
        dependency = state.get(action.get('project'), {})
        if action['kind'] == 'send_release':
            satisfied = active and dependency.get('ready') is True and dependency.get('revision') == action.get('revision')
        else:
            satisfied = bool(active and obligation and 'blocked_at' in obligation
                             and last['elapsed_secs'] >= obligation['blocked_at'] and not dependency.get('ready'))
        evidence.append({'action_seq': row['seq'], 'project': action.get('project'),
                         'read_seq': last['seq'] if last else None,
                         'observed_elapsed_secs': last.get('elapsed_secs') if last else None,
                         'observed_precondition_satisfied': bool(satisfied)})
    return {'version': DIAGNOSTICS_VERSION, 'violations': sum(not e['observed_precondition_satisfied'] for e in evidence),
            'actions': evidence, 'limitation': 'Read attribution assumes the declared single operational worker.'}


def retained_receipts(run_dir: Path, rows):
    """Check numeric native receipt references, without treating prose as proof."""
    files = list((run_dir / 'runtime-traces').rglob('responsibility/receipts.md'))
    expected = [r.get('receipt', r['seq']) for r in rows if r['kind'] == 'action' and r['action'].get('kind') != 'memory']
    if len(files) != 1:
        return {'measured': False, 'reason': 'no unique native receipt log', 'expected_receipts': expected}
    text = files[0].read_text()
    # Receipt values are simulator sequence ids. JSON, Markdown tables and
    # explicit "receipt 14" references are accepted; arbitrary numbers are not.
    ids = set(int(n) for n in re.findall(r'["\']?receipt["\']?\s*[:=#]?\s*["\']?(\d+)', text, re.I))
    receipt_columns = []
    for line in text.splitlines():
        if '|' not in line:
            continue
        cells = [c.strip().strip('`') for c in line.strip().strip('|').split('|')]
        headers = [i for i, cell in enumerate(cells) if 'receipt' in cell.lower()]
        if headers:
            receipt_columns = headers
        else:
            ids.update(int(cells[i]) for i in receipt_columns if i < len(cells) and cells[i].isdigit())
    return {'measured': True, 'expected_receipts': expected, 'retained_receipts': sorted(ids & set(expected)),
            'missing_receipts': sorted(set(expected) - ids),
            'limitation': 'Numeric references only; content truth and append-only history require a separate mutation audit.'}
