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


RECEIPT_CONTENT_VERSION = 2
_JSON_RECEIPT = re.compile(r'["\']receipt["\']\s*:\s*(\d+)', re.I)
_PROSE_RECEIPT = re.compile(r'\breceipt\b\s*[:=#]?\s*(\d+)', re.I)
_KIND = re.compile(r'["\']kind["\']\s*:\s*["\'](\w+)["\']')
_PROJECT = re.compile(r'["\']project["\']\s*:\s*["\']([^"\']+)["\']')
_BARE_KIND = re.compile(r'\b(send_release|request_input|memory)\b')


def receipt_log_entries(text):
    """Split a model-authored receipt log into entries.

    A Markdown table row is one entry; otherwise a heading starts an entry
    and following lines belong to it. Header and separator rows are skipped.
    """
    entries, current = [], []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('|') or stripped.count('|') >= 2:
            if current:
                entries.append('\n'.join(current)); current = []
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            if all(set(c) <= set('-: ') for c in cells) or not _KIND.search(stripped) and not _JSON_RECEIPT.search(stripped):
                continue  # separator or header row
            entries.append(stripped)
        elif stripped.startswith('#'):
            if current:
                entries.append('\n'.join(current))
            current = [stripped]
        elif stripped:
            current.append(stripped)
    if current:
        entries.append('\n'.join(current))
    return entries


def _payloads(entry):
    """Payload (position, kind, project) in order; memory carries no project."""
    found = []
    for match in _KIND.finditer(entry):
        kind = match.group(1)
        if kind not in ('send_release', 'request_input', 'memory'):
            continue
        project = None
        if kind != 'memory':
            following = _PROJECT.search(entry, match.end())
            project = following.group(1) if following else None
        found.append((match.start(), kind, project))
    return found


def receipt_claims(entry):
    """The (receipt, kind, project) claims one entry asserts.

    Each HTTP-response JSON receipt pairs with the nearest payload before it,
    so one section logging several actions yields several claims. Without
    JSON receipts, a single prose receipt number pairs with a single payload
    (or a single bare action word). Returns None when the entry is ambiguous.
    """
    payloads = _payloads(entry)
    if not payloads and set(_BARE_KIND.findall(entry)) == {'memory'}:
        payloads = [(0, 'memory', None)]  # a memory row described in prose
    receipts = [(m.start(), int(m.group(1))) for m in _JSON_RECEIPT.finditer(entry)]
    claims = []
    if receipts:
        for position, number in receipts:
            before = [p for p in payloads if p[0] < position]
            source = before[-1] if before else (payloads[0] if len(payloads) == 1 else None)
            if source is None or (source[1] != 'memory' and source[2] is None):
                return None
            claims.append({'receipt': number, 'kind': source[1], 'project': source[2]})
        return claims
    numbers = {int(n) for n in _PROSE_RECEIPT.findall(entry)}
    if len(numbers) != 1:
        return None
    if len(payloads) == 1:
        _, kind, project = payloads[0]
    else:
        return None
    if kind != 'memory' and project is None:
        return None
    return [{'receipt': numbers.pop(), 'kind': kind, 'project': project}]


def retained_receipts_by_content(run_dir: Path, rows):
    """Match logged receipts to the simulator's action ledger by content.

    A logged receipt counts only when the ledger action carrying that receipt
    has the same kind and project. A logged receipt whose number names a
    different (or no) ledger action is a contradicted claim, even when the
    number itself exists in the ledger.
    """
    files = list((run_dir / 'runtime-traces').rglob('responsibility/receipts.md'))
    ledger = {r.get('receipt', r['seq']): r['action'] for r in rows if r['kind'] == 'action'}
    expected = sorted(k for k, a in ledger.items() if a.get('kind') != 'memory')
    if len(files) != 1:
        return {'version': RECEIPT_CONTENT_VERSION, 'measured': False, 'reason': 'no unique native receipt log',
                'expected_receipts': expected}
    claims, unparsed = [], 0
    for entry in receipt_log_entries(files[0].read_text()):
        found = receipt_claims(entry)
        if found is None:
            # Titles and prose without any receipt or payload are not entries.
            unparsed += bool(_JSON_RECEIPT.search(entry) or _KIND.search(entry))
        else:
            claims.extend(found)
    matched, contradicted = set(), []
    for claim in claims:
        action = ledger.get(claim['receipt'])
        if (action is not None and action.get('kind') == claim['kind']
                and (claim['kind'] == 'memory' or action.get('project') == claim['project'])):
            matched.add(claim['receipt'])
        else:
            contradicted.append(claim | {'ledger_kind': action.get('kind') if action else None,
                                         'ledger_project': action.get('project') if action else None})
    unique = []
    for claim in contradicted:
        if claim not in unique:
            unique.append(claim)
    return {'version': RECEIPT_CONTENT_VERSION, 'measured': True, 'expected_receipts': expected,
            'retained_receipts': sorted(matched & set(expected)),
            'missing_receipts': sorted(set(expected) - matched),
            'contradicted_claims': unique, 'unparsed_entries': unparsed,
            'limitation': 'Matches receipt number, action kind and project against the simulator ledger. '
                          'Entries without exactly one receipt number and one payload kind/project are '
                          'counted as unparsed, not as evidence either way.'}
