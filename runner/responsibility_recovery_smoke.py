#!/usr/bin/env python3
"""Zero-real-LLM native failed-code-job recovery; never a strategy score.

Reproduce the active-parser bug, observe three failed native fires, patch via
the real file tool, run offline tests, restore scheduler eligibility, restart,
and demand scheduled successes without forcing a healthy fire.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import time
from pathlib import Path
from types import SimpleNamespace

from continuity_peko import PekoDriver
from responsibility_surface_smoke import ScriptedProvider, SmokeClaw
from responsibility_prepared import prepare_peko, prepare_claw
import responsibility_strategy as strategy

ROOT = Path(__file__).resolve().parent.parent
BAD_PARSE = 'start, end = raw.find("```json"), raw.find("```", start+7) if "```json" in raw else -1'
GOOD_PARSE = 'start = raw.find("```json"); end = raw.find("```", start+7) if start >= 0 else -1'
SCRIPT = '''import json, sys, time
from pathlib import Path
def parse(raw):
    PARSER
    return json.loads(raw[start+7:end] if start >= 0 else raw)
def decide(raw):
    world = parse(raw)
    return "active" if world["watch_active"] else "inactive"
if "--self-test" in sys.argv:
    assert decide('```json\\n{"watch_active":true}\\n```') == "active"
    assert decide('{"watch_active":false}') == "inactive"
    response = parse('{"receipts":[{"receipt":7,"action_key":"send_release:fictional"}]}')
    assert response["receipts"][0]["action_key"] == "send_release:fictional"
    print("PREFLIGHT_OK active inactive receipts")
else:
    assert decide('```json\\n{"watch_active":true}\\n```') == "active"
    with Path(sys.argv[1]).open("a") as stream:
        stream.write(json.dumps({"marker":"RECOVERY_OK","wall_time":time.time()})+"\\n")
'''


def run(name, out):
    out.mkdir(parents=True)
    provider = ScriptedProvider()
    os.environ.update(PEKO_API_KEY='scripted-no-real-key', PEKO_BASE_URL=provider.url,
        PEKO_MODEL_NAME='mimo-v2.6-flash', PEKO_MODEL_ID='mimo-v2.6-flash',
        PEKO_API_FORMAT='anthropic_messages', PEKO_CONTEXT_WINDOW='1048576',
        PEKO_MAX_OUTPUT_TOKENS='4096', PEKO_MODEL_SPEC=json.dumps({
            'tool_support':'function_calling','streaming':True,'thinking':'optional',
            'pricing':{'input_per_million':.14,'output_per_million':.28}}))
    driver = (PekoDriver if name == 'peko' else SmokeClaw)(out, 300, .1)
    checks, errors, metadata, snapshots = [], [], {}, []

    def invoke(tool, args):
        provider.steps.append((tool,args))
        driver.turn('SCRIPTED_RECOVERY_SURFACE: execute supplied call and finish.')
        call = provider.calls[-1]
        result = provider.results.get(call['id'],{})
        checks.append({'check':'native-'+tool,'passed':bool(result) and not result.get('is_error',False),
                       'wire_call':call,'native_result':result})
        if not checks[-1]['passed']:
            raise ValueError('native repair tool failed: '+tool)
        return result

    def state():
        if name == 'peko':
            home = Path(driver.temp.name)/'.peko/data/principals'/driver.principal
            value = json.loads(next(home.rglob('cron/schedule.toml')).read_text())
            job = next(j for j in value['jobs'] if j.get('name')=='recovery-code')
            runs = [r for r in value['runs'] if r['job_id']==job['id'] and r['status']!='running']
        else:
            value = json.loads(driver._command('automations','list','--all','--json'))
            job = next(j for j in value['jobs'] if j.get('name')=='recovery-code')
            runs = [r for r in strategy.claw_runs(driver)['entries'] if r.get('jobId')==job['id'] and r.get('action')=='finished']
        return {'job':job,'runs':runs}

    def wait_runs(minimum, timeout=30):
        until = time.monotonic()+timeout
        while True:
            value = state()
            if len(value['runs'])>=minimum:
                return value
            if time.monotonic()>=until:
                raise TimeoutError('native terminal run history did not reach '+str(minimum))
            time.sleep(.2)

    try:
        metadata = driver.start()
        driver.sim = SimpleNamespace(spec={'execution_policy':'strategy-choice','cadence_secs':60})
        if name == 'peko':
            workspace = Path(driver.temp.name)/'.peko/principals'/driver.principal
            source = Path(os.environ.get('PEKO_WORKFLOW_SDK_SOURCE',str(Path(os.environ['PEKO_BIN']).resolve().parents[2]/'sdks/python/peko_workflow/src/peko_workflow')))
            driver.config_env['PEKO_WORKFLOW_SDK_SOURCE'] = str(source)
            prepare_peko(driver,'SCRIPTED_FIXTURE: controller marker, no obligation facts.')
        else:
            workspace = driver.workspace
            prepare_claw(driver,'SCRIPTED_FIXTURE: controller marker, no obligation facts.')
        script = workspace/'workflows/recovery.py'
        marker = workspace/'recovery.jsonl'
        write, field = ('Write','file_path') if name=='peko' else ('write','path')
        invoke(write,{field:str(script),'content':SCRIPT.replace('PARSER',BAD_PARSE)})
        cli = shlex.join([driver.node,str(driver.entry)]) if name!='peko' else None
        if name=='peko':
            invoke('CronCreate',{'tool':'Workflow','params':{'path':script.name,'args':[str(marker)]},
                'interval_ms':5000,'label':'recovery-code','wake_on_completion':False,'timeout_secs':10})
        else:
            argv = shlex.quote(json.dumps(['python3',str(script),str(marker)]))
            invoke('exec',{'command':f'{cli} automations add --name recovery-code --every 5s --command-argv {argv} --command-cwd {shlex.quote(str(workspace))} --timeout-seconds 10 --no-deliver --json'})
        job_id = state()['job']['id']
        if name=='peko':
            for _ in range(3):
                before = len(state()['runs'])
                invoke('CronTrigger',{'id':job_id})
                wait_runs(before+1)
        else:
            # Force/debug runs preserve schedule state and do not establish
            # timer backoff. Observe actual scheduled failures (5s, +30s, +60s).
            wait_runs(3,120)
        failed = state(); snapshots.append({'stage':'failed','native':failed})
        statuses = [r['status'] for r in failed['runs']]
        failure = 'failed' if name=='peko' else 'error'  # Persisted native history vocabularies differ.
        checks.append({'check':'active-parser-native-failures','passed':len(statuses)>=3 and all(s==failure for s in statuses) and not marker.exists(), 'statuses':statuses})
        if name=='peko':
            failed_gate = not failed['job']['enabled'] and failed['job']['consecutive_failures']>=3
            returned_ids = [json.loads(c['native_result']['content'])['run_id'] for c in checks if c['check']=='native-CronTrigger']
            checks.append({'check':'trigger-ids-match-persisted-history','passed':set(returned_ids)<=set(r['id'] for r in failed['runs']), 'returned_ids':returned_ids})
            invoke('CronHistory',{'id':job_id})
        else:
            j = failed['job']; s = j['state']
            failed_gate = s.get('consecutiveErrors',0)>=3 and s.get('nextRunAtMs',0)-time.time()*1000>240000
            invoke('exec',{'command':f'{cli} automations runs --id {shlex.quote(job_id)} --json'})
        checks.append({'check':'failure-eligibility-observed','passed':failed_gate})
        invoke(write,{field:str(script),'content':SCRIPT.replace('PARSER',GOOD_PARSE)})
        repaired_file = state(); snapshots.append({'stage':'file-only-repair','native':repaired_file})
        checks.append({'check':'file-repair-does-not-reset-scheduler','passed':repaired_file['job']==failed['job']})
        command = 'python3 '+shlex.quote(str(script))+' --self-test'
        result = invoke('Bash' if name=='peko' else 'exec',{'command':command})
        checks.append({'check':'offline-active-inactive-receipt-preflight','passed':'PREFLIGHT_OK' in str(result) and not marker.exists()})
        if name=='peko':
            invoke('CronUpdate',{'id':job_id,'enabled':True})
        else:
            invoke('exec',{'command':f'{cli} automations edit {shlex.quote(job_id)} --enable --every 5s --json'})
            same = state(); snapshots.append({'stage':'same-enabled-edit','native':same})
            checks.append({'check':'same-enabled-edit-retains-next-due','passed':same['job']['state'].get('consecutiveErrors')==0 and same['job']['state'].get('nextRunAtMs')==failed['job']['state'].get('nextRunAtMs')})
            invoke('exec',{'command':f'{cli} automations edit {shlex.quote(job_id)} --disable --json'})
            invoke('exec',{'command':f'{cli} automations edit {shlex.quote(job_id)} --enable --every 5s --json'})
        recovered = state(); snapshots.append({'stage':'re-enabled','native':recovered})
        checks.append({'check':'failure-budget-reset','passed':recovered['job']['enabled'] and (recovered['job'].get('consecutive_failures',0) if name=='peko' else recovered['job']['state'].get('consecutiveErrors',0))==0})
        if name!='peko':
            checks.append({'check':'pause-resume-rearms-next-due','passed':recovered['job']['state'].get('nextRunAtMs',float('inf'))<=time.time()*1000+10000})
        requests_before = len(provider.catalogs)
        restarted = driver.restart()
        until = time.monotonic()+60
        while time.monotonic()<until:
            rows = [json.loads(line) for line in marker.read_text().splitlines()] if marker.exists() else []
            if len(rows)>=2:
                break
            time.sleep(.2)
        terminal = state(); snapshots.append({'stage':'scheduled-after-restart','native':terminal})
        success = 'success' if name=='peko' else 'ok'
        checks.append({'check':'native-restart','passed':restarted.get('restart_verified',False)})
        checks.append({'check':'scheduled-recovery-without-manual-success-fire','passed':len(rows)>=2 and any(r['status']==success for r in terminal['runs']), 'markers':rows})
        checks.append({'check':'recovery-fires-without-model-request','passed':len(provider.catalogs)==requests_before,'requests_during_wait':len(provider.catalogs)-requests_before})
    except Exception as exc:
        errors.append(f'{type(exc).__name__}: {exc}')
    finally:
        try:
            driver.close()
        except Exception as exc:
            errors.append(f'cleanup {type(exc).__name__}: {exc}')
        provider.close()
    result = {'evidence_kind':'scripted_native_failure_recovery_not_model_strategy','real_llm_calls':0,
        'driver':name,'metadata':metadata,'checks':checks,'errors':errors,'native_snapshots':snapshots,
        'source_manifest':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('runner/responsibility*.py')},
        'passed':not errors and bool(checks) and all(c['passed'] for c in checks)}
    (out/'result.json').write_text(driver._redact(json.dumps(result,indent=2)))
    print(json.dumps({'driver':name,'passed':result['passed'],'errors':errors,'report':str(out),
        'checks':[{k:v for k,v in c.items() if k not in ('wire_call','native_result')} for c in checks]},indent=2),flush=True)
    return result


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver',choices=('peko','openclaw'),required=True)
    args = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    raise SystemExit(0 if run(args.driver,ROOT/'reports'/f'{stamp}-recovery-surface-{args.driver}')['passed'] else 1)
