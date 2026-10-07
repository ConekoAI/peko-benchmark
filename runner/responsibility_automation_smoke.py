#!/usr/bin/env python3
"""Real native automation paths with scripted responses and zero real LLM calls.

Controller-authored marker scripts are surface probes, never strategy scores.
Both harnesses must execute code directly, recur, fire a one-shot, and survive a
process restart without contacting a model at each fire.
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
import responsibility_strategy as strategy
from responsibility_prepared import prepare_peko, prepare_claw, arm_peko, set_claw_due_times, pause_peko_for_probe, pause_claw_for_probe

ROOT = Path(__file__).resolve().parent.parent


def run(name, out):
    out.mkdir(parents=True)
    provider = ScriptedProvider()
    os.environ.update(PEKO_API_KEY='scripted-no-real-key', PEKO_BASE_URL=provider.url,
        PEKO_MODEL_NAME='mimo-v2.6-flash', PEKO_MODEL_ID='mimo-v2.6-flash',
        PEKO_API_FORMAT='anthropic_messages', PEKO_CONTEXT_WINDOW='1048576',
        PEKO_MAX_OUTPUT_TOKENS='4096', PEKO_MODEL_SPEC=json.dumps({
            'tool_support':'function_calling', 'streaming':True, 'thinking':'optional',
            'pricing':{'input_per_million':.14, 'output_per_million':.28}}))
    driver = (PekoDriver if name == 'peko' else SmokeClaw)(out, 300, .1)
    checks, errors, metadata, restart = [], [], {}, {}
    watch_start = watch_end = None

    def snapshot(stage):
        if name == 'peko':
            home = Path(driver.temp.name)/'.peko/data/principals'/driver.principal
            schedule = json.loads(next(home.rglob('cron/schedule.toml')).read_text())
            sessions = json.loads(next(home.rglob('sessions.json')).read_text())
        else:
            schedule = json.loads(driver._command('automations','list','--all','--json'))
            sessions = json.loads(driver._command('sessions','--all-agents','--json'))
        check = strategy.verify(name, schedule, sessions, 60, stage)
        checks.append({'check':'strategy-fixture-' + stage, 'passed':check['verified'], 'errors':check['errors']})
        (out/f'topology-{stage}.json').write_text(driver._redact(json.dumps({'schedule':schedule,'sessions':sessions,'check':check},indent=2)))

    def invoke(tool, args):
        provider.steps.append((tool, args))
        driver.turn('SCRIPTED_AUTOMATION_SURFACE: execute supplied tool call and finish.')
        call = provider.calls[-1]
        result = provider.results.get(call['id'], {})
        checks.append({'check':'native-' + tool, 'passed':bool(result) and not result.get('is_error', False),
                       'wire_call':call, 'native_result':result})
        return result

    try:
        metadata = driver.start()
        driver.sim = SimpleNamespace(spec={'execution_policy':'strategy-choice','cadence_secs':60})
        if name == 'peko':
            workspace = Path(driver.temp.name)/'.peko/principals'/driver.principal
            source = Path(os.environ.get('PEKO_WORKFLOW_SDK_SOURCE',
                str(Path(os.environ['PEKO_BIN']).resolve().parents[2]/'sdks/python/peko_workflow/src/peko_workflow')))
            driver.config_env['PEKO_WORKFLOW_SDK_SOURCE'] = str(source)
            prepare_peko(driver, 'SCRIPTED_FIXTURE: no commitment facts; marker procedures are controller probes.')
        else:
            workspace = driver.workspace
            prepare_claw(driver, 'SCRIPTED_FIXTURE: no commitment facts; marker procedures are controller probes.')
            driver._command('config','set','agents.defaults.heartbeat.prompt',strategy.supervisor(60))
        snapshot('post-setup')
        scripts = workspace/'workflows'; scripts.mkdir(exist_ok=True)
        script = scripts/'surface_marker.py'
        script.write_text('import sys, time, json\nfrom pathlib import Path\n'
            'target = Path(sys.argv[1])\n'
            'with target.open("a") as stream: stream.write(json.dumps({"marker":"AUTOMATION_OK","wall_time":time.time()})+"\\n")\n')
        if name == 'peko':
            callback = scripts/'surface_callback.py'
            callback.write_text('import os, sys\nfrom pathlib import Path\n'
                'sys.path.insert(0, str(Path(os.environ["PEKO_WORKSPACE"])/".benchmark-sdk"))\n'
                'import peko_workflow as peko\n'
                'print(peko.tools.call("Write", file_path=sys.argv[1], content="CALLBACK_OK"))\n')
            invoke('Workflow', {'path':callback.name, 'args':[str(workspace/'callback.txt')], 'timeout_ms':10000})
            checks.append({'check':'conversational-workflow-sdk-Write',
                           'passed':(workspace/'callback.txt').exists() and (workspace/'callback.txt').read_text()=='CALLBACK_OK'})
            invoke('CronCreate', {'tool':'Workflow', 'params':{'path':script.name,'args':[str(workspace/'recurring.jsonl')]},
                'interval_ms':5000,'label':'surface-recurring-code','wake_on_completion':False,'timeout_secs':10})
            at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=45)
            invoke('CronCreate', {'tool':'Workflow', 'params':{'path':callback.name,'args':[str(workspace/'scheduled-callback.txt')]},
                'at':at.isoformat(),'label':'surface-once-workflow','wake_on_completion':False,'timeout_secs':10})
            invoke('CronCreate', {'tool':'Bash', 'params':{'command':'python3 ' + shlex.quote(str(script)) + ' ' + shlex.quote(str(workspace/'once.jsonl'))},
                'at':at.isoformat(),'label':'surface-once-tool','wake_on_completion':False,'timeout_secs':10})
        else:
            invoke('exec', {'command':'python3 ' + shlex.quote(str(script)) + ' ' + shlex.quote(str(workspace/'direct.jsonl'))})
            checks.append({'check':'conversational-python-exec', 'passed':(workspace/'direct.jsonl').exists()})
            cli = shlex.join([driver.node,str(driver.entry)])
            command = shlex.quote(json.dumps(['python3',str(script),str(workspace/'recurring.jsonl')]))
            invoke('exec', {'command':f'{cli} automations add --name surface-recurring-code --every 5s --command-argv {command} --command-cwd {shlex.quote(str(workspace))} --timeout-seconds 10 --no-deliver --json'})
            at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=45)
            command = shlex.quote(json.dumps(['python3',str(script),str(workspace/'once.jsonl')]))
            invoke('exec', {'command':f'{cli} automations add --name surface-once-tool --at {shlex.quote(at.isoformat())} --command-argv {command} --command-cwd {shlex.quote(str(workspace))} --timeout-seconds 10 --no-deliver --delete-after-run --json'})
        (arm_peko if name == 'peko' else lambda d:set_claw_due_times(d, armed=True))(driver)
        snapshot('pre-watch')
        requests_before = len(provider.catalogs)  # Includes text-only requests, not just tool calls.
        watch_start = time.time()
        checks.append({'check':'one-shot-pending-before-restart','passed':not (workspace/'once.jsonl').exists()})
        restart = driver.restart()
        snapshot('post-restart')
        until = time.monotonic()+60
        while time.monotonic()<until:
            recurring = workspace/'recurring.jsonl'
            count = len(recurring.read_text().splitlines()) if recurring.exists() else 0
            if count >= 2 and (workspace/'once.jsonl').exists() and (name != 'peko' or (workspace/'scheduled-callback.txt').exists()):
                break
            time.sleep(.2)
        checks.append({'check':'native-process-restart','passed':restart.get('restart_verified',False)})
        checks.append({'check':'recurring-code-after-restart','passed':count >= 2,'observed_invocations':count})
        once = workspace/'once.jsonl'
        rows = [json.loads(line) for line in once.read_text().splitlines()] if once.exists() else []
        checks.append({'check':'one-shot-code-after-restart','passed':len(rows)==1 and rows[0]['wall_time']>=watch_start,
                       'dispatch_delay_secs':rows[0]['wall_time']-at.timestamp() if rows else None})
        if name == 'peko':
            checks.append({'check':'one-shot-workflow-sdk-after-restart', 'passed':(workspace/'scheduled-callback.txt').exists()
                           and (workspace/'scheduled-callback.txt').read_text()=='CALLBACK_OK'})
        checks.append({'check':'code-fires-without-model-request','passed':len(provider.catalogs)==requests_before,
                       'requests_during_wait':len(provider.catalogs)-requests_before})
        watch_end = time.time()
        snapshot('post-watch')
        if name == 'peko':
            home = Path(driver.temp.name)/'.peko/data/principals'/driver.principal
            native = json.loads(next(home.rglob('cron/schedule.toml')).read_text())
        else:
            native = strategy.claw_runs(driver)
            (out/'strategy-native-runs.json').write_text(driver._redact(json.dumps(native,indent=2)))
        (out/'native-runs.json').write_text(driver._redact(json.dumps(native,indent=2)))
        (pause_peko_for_probe if name == 'peko' else pause_claw_for_probe)(driver)
        if name == 'peko':
            native = json.loads(next(home.rglob('cron/schedule.toml')).read_text())
            enabled = [j for j in native['jobs'] if j.get('enabled')]
        else:
            native = json.loads(driver._command('automations','list','--all','--json'))
            enabled = [j for j in native.get('jobs',[]) if j.get('enabled') and not
                       j.get('declarationKey','').startswith(('memory-core:','skill-collection-review:'))]
        checks.append({'check':'probe-isolation-disables-chosen-jobs','passed':not enabled})
    except Exception as exc:
        errors.append(f'{type(exc).__name__}: {exc}')
    finally:
        try:
            driver.close()
        except Exception as exc:
            errors.append(f'cleanup {type(exc).__name__}: {exc}')
        provider.close()
    if watch_start is not None and watch_end is not None:
        evidence = strategy.execution_evidence(out,watch_start,watch_end)
        (out/'strategy-execution.json').write_text(json.dumps(evidence,indent=2))
        checks.append({'check':'native-strategy-execution-evidence','passed':evidence['verified']})
    sources = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in ROOT.glob('runner/responsibility*.py')}
    result = {'evidence_kind':'scripted_native_automation_surface_not_model_strategy', 'real_llm_calls':0,
              'driver':name,'metadata':metadata,'restart':restart,'checks':checks,'errors':errors,
              'source_manifest':sources,'passed':not errors and bool(checks) and all(c['passed'] for c in checks)}
    (out/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'driver':name,'passed':result['passed'],'errors':errors,
                      'checks':[{k:v for k,v in c.items() if k not in ('wire_call','native_result')} for c in checks],
                      'report':str(out)},indent=2),flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver',choices=('peko','openclaw'),required=True)
    args = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    result = run(args.driver,ROOT/'reports'/f'{stamp}-automation-surface-{args.driver}')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
