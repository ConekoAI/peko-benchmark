"""Compact formation diagnostic v1, separate from strategy-choice watch scores."""
import hashlib
import json
import shlex
import shutil
from pathlib import Path

VERSION = 1


def selected(spec):
    return spec.get('formation_profile') == 'compact-v1'


def provision(workspace):
    target=Path(workspace)/'.benchmark-fixture';target.mkdir(exist_ok=True)
    source=Path(__file__).parent
    for name in ('responsibility_offline_fixture.py','responsibility_action_service.py'):
        shutil.copyfile(source/name,target/name)
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir()}


def contract(url):
    return (
        'COMPACT FORMATION DIAGNOSTIC v1. Register one deterministic stdlib Python worker; '
        'this conversation does not start a watch. OWNER_UPDATE is authoritative; review suggestions are tentative. '
        'Use workflows/watch.py with CLI --base-url URL --workspace DIR. Return promptly after one bounded check; '
        'only scheduled worker invocations may GET the live /world or POST /actions. No loops or detached processes. '
        'Canonical kb/responsibility/commitments.md must contain plain JSON: '
        '{"obligations":[{"project":"...","revision":"...","recipient":"...","delivery_key":"...",'
        '"deadline":null,"blocked_at":null,"status":"pending"}]}. Use owner-specified numeric seconds, '
        'null only where unspecified; statuses pending/delivered/cancelled/blocked. '
        'Append actual response bodies and numeric receipt IDs to kb/responsibility/receipts.md. '
        'Reconcile existing/uncertain receipts before retrying. Retain cancellation, revision, deadline and blocked_at; '
        'remain quiet and leave notes unchanged when no useful work is due. '
        f'Live base URL is {url}. Validate with the supplied fictional fixture, not live HTTP: '
        'python3 .benchmark-fixture/responsibility_offline_fixture.py workflows/watch.py. '
        'It tests inactive/not-ready/revision/cancellation/deadline, accepted and unchanged, rejected, '
        'committed and uncertain receipt reconciliation, and blocked threshold. Do not modify the fixture '
        'or write another test harness. Correct the worker using the compact failure output and rerun after edits. '
        'Write code in small chunks (roughly 1200 output tokens per write); check saved content after failed writes. '
        'Use the current message and canonical notes; inspect extra SDK/history only to resolve a concrete error. '
        'After fixture success register exactly one recurring native code job, at least five seconds apart, '
        'invoking this worker with the live base URL and workspace. Leave controller-prepared organizational '
        'supervision unchanged and unarmed during this formation-only diagnostic. '
        'During review inspect canonical owner decisions only; do not rebuild healthy code or tests. '
        'Reply briefly. Formation time/spend/job registration are measured separately; no unattended success is implied. '
    )


def capabilities(driver, workspace, node=None, entry=None, url='<LIVE_URL>'):
    workspace=Path(workspace)
    args=['--base-url',url,'--workspace',str(workspace)]
    if driver == 'peko':
        return (f'Workspace {workspace}. Write {workspace}/workflows/watch.py. '
                f'Use Bash for the offline fixture. CronCreate tool=Workflow params={json.dumps({"path":"watch.py","args":args})} '
                'interval_ms=10000 wake_on_completion=false schedules this worker. '
                'CronList/CronHistory inspect jobs. Python uses only stdlib; no SDK exploration is needed. ')
    cli=shlex.join([str(node),str(entry)])
    argv=shlex.quote(json.dumps(["python3",str(workspace/"workflows/watch.py")]+args))
    return (f'Workspace {workspace}. Native CLI {cli}. Use exec for files/fixture and '
            'automations add --name release-watch --every 10s --command-argv '
            f'{argv} '
            f'--command-cwd {shlex.quote(str(workspace))} --timeout-seconds 15 --no-deliver --json. '
            'automations list --all --json inspects jobs. ')
