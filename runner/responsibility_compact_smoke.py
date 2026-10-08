#!/usr/bin/env python3
"""Native compact-profile reachability with scripted responses, zero real LLM."""
import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import sys
import time
from pathlib import Path
from responsibility_surface_smoke import ScriptedProvider
from responsibility_drivers import PekoResponsibility, ClawResponsibility
from responsibility_simulator import Simulator, load_spec
from responsibility_formation import gate
import responsibility_compact as compact
from responsibility_strategy import claw_runs

ROOT=Path(__file__).resolve().parent.parent


def fixture_passed(value):
    if isinstance(value,str):
        try: return fixture_passed(json.loads(value))
        except (ValueError,TypeError): return False
    if isinstance(value,dict):
        if value.get('fixture_version')==1: return value.get('passed') is True
        return any(fixture_passed(v) for v in value.values())
    if isinstance(value,list): return any(fixture_passed(v) for v in value)
    return False


def run(name,out):
    out.mkdir(parents=True)
    provider=ScriptedProvider()
    os.environ.update(PEKO_API_KEY='scripted-no-real-key',PEKO_BASE_URL=provider.url,
        PEKO_MODEL_NAME='mimo-v2.6-flash',PEKO_MODEL_ID='mimo-v2.6-flash',
        PEKO_API_FORMAT='anthropic_messages',PEKO_CONTEXT_WINDOW='1048576',
        PEKO_MAX_OUTPUT_TOKENS='4096',PEKO_MODEL_SPEC=json.dumps({
            'tool_support':'function_calling','streaming':True,'thinking':'optional',
            'pricing':{'input_per_million':.14,'output_per_million':.28}}))
    spec=load_spec(ROOT/'scenarios/responsibility/pilot.toml',1)
    spec.update(formation_profile='compact-v1',execution_policy='strategy-choice',formation='prepared',
                topology='separated',action_mode='guarded',profile_prompt=True)
    fictional={'project':'fictional-alpha','revision':'r2','recipient':'fictional-room',
               'delivery_key':'fictional-key','deadline':30,'blocked_at':None,'status':'pending'}
    spec['obligations']=[fictional]
    sim=Simulator(spec,out);sim.start_server()
    driver=(PekoResponsibility if name=='peko' else ClawResponsibility)(out,300,.1,sim,'supervisory')
    checks=[];errors=[];metadata={};result_gate=None

    def invoke(tool,args):
        provider.steps.append((tool,args))
        driver.conversation('SCRIPTED_COMPACT_SURFACE: execute the supplied call and finish.')
        call=provider.calls[-1];result=provider.results.get(call['id'],{})
        passed=bool(result) and not result.get('is_error',False)
        checks.append({'tool':tool,'passed':passed,'wire_call':call,'native_result':result})
        if not passed: raise ValueError('native compact surface failed: '+tool)
        return result

    try:
        metadata=driver.start();driver.validate_topology('post-setup')
        workspace=(Path(driver.temp.name)/'.peko/principals'/driver.principal if name=='peko' else driver.workspace)
        # Certification implementation belongs only to this scripted probe.
        # Neither the live runner nor provision() supplies it to a model.
        sys.path.insert(0,str(ROOT/'tests'))
        from test_responsibility_compact import REFERENCE
        write,field=('Write','file_path') if name=='peko' else ('write','path')
        invoke(write,{field:str(workspace/'workflows/watch.py'),'content':REFERENCE})
        if name=='peko':
            before=len(provider.calls)
            provider.steps.extend([('Write',{}),('Write',{'file_path':str(workspace/'output-recovered.txt'),
                                                        'content':'NATIVE_OUTPUT_RECOVERY'})])
            provider.stop_reasons.append('max_tokens')
            driver.conversation('SCRIPTED_OUTPUT_RECOVERY: execute supplied calls and finish.')
            calls=provider.calls[before:]
            checks.append({'check':'native-empty-write-output-limit-continuation',
                'passed':len(calls)==2 and provider.results[calls[0]['id']].get('is_error',False)
                     and not provider.results[calls[1]['id']].get('is_error',False)
                     and (workspace/'output-recovered.txt').read_text()=='NATIVE_OUTPUT_RECOVERY',
                'wire_calls':calls,'native_results':[provider.results.get(c['id']) for c in calls]})
        invoke(write,{field:str(workspace/'kb/responsibility/commitments.md'),
                      'content':json.dumps({'obligations':[fictional]})})
        fixture_command=shlex.join(['python3',str(workspace/'.benchmark-fixture/responsibility_offline_fixture.py'),
                                  str(workspace/'workflows/watch.py')])
        result=invoke('Bash' if name=='peko' else 'exec',{'command':fixture_command})
        checks.append({'check':'supplied-fictional-fixture-through-native-shell',
                       'passed':fixture_passed(result)})
        if name=='peko':
            invoke('CronCreate',{'tool':'Workflow','params':{'path':'watch.py','args':[
                '--base-url',sim.url,'--workspace',str(workspace)]},'interval_ms':10000,
                'label':'release-watch','wake_on_completion':False,'timeout_secs':15})
        else:
            prompt=compact.capabilities(name,workspace,driver.node,driver.entry,url=sim.url)
            suffix=prompt.split('automations add',1)[1].split('. automations list',1)[0]
            cli=shlex.join([driver.node,str(driver.entry)])
            invoke('exec',{'command':cli+' automations add'+suffix})
        requests_before=len(provider.catalogs)
        until=time.monotonic()+30
        runs=[]
        while time.monotonic()<until:
            if name=='peko':
                root=Path(driver.temp.name)/'.peko/data/principals'/driver.principal
                schedule=json.loads(next(root.rglob('cron/schedule.toml')).read_text())
                job=next(j for j in schedule['jobs'] if j.get('name')=='release-watch')
                runs=[r for r in schedule['runs'] if r['job_id']==job['id'] and r['status']=='success']
            else:
                runs=[r for r in claw_runs(driver)['entries'] if r.get('action')=='finished' and r.get('status')=='ok']
            if runs and any(r['kind']=='read' for r in sim.rows): break
            time.sleep(.2)
        checks.append({'check':'native-scheduled-worker-reaches-inactive-live-world-without-llm',
                       'passed':bool(runs) and any(r['kind']=='read' for r in sim.rows)
                                and len(provider.catalogs)==requests_before,'native_runs':runs,
                       'requests_during_scheduled_wait':len(provider.catalogs)-requests_before})
        result_gate=gate(driver,workspace)
    except Exception as exc: errors.append(f'{type(exc).__name__}: {exc}')
    finally:
        try: driver.close()
        except Exception as exc: errors.append(f'cleanup: {type(exc).__name__}: {exc}')
        sim.close();provider.close()
    result={'evidence_kind':'scripted_compact_formation_reachability_not_model_strategy',
        'real_llm_calls':0,'driver':name,'metadata':metadata|dict(driver.metadata),'checks':checks,
        'errors':errors,'formation_gate':result_gate,'watch_started':False,
        'source_manifest':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in ROOT.glob('runner/responsibility*.py')},
        'passed':not errors and bool(result_gate and result_gate['passed']) and all(c['passed'] for c in checks)}
    (out/'result.json').write_text(driver._redact(json.dumps(result,indent=2)))
    print(json.dumps({'driver':name,'passed':result['passed'],'errors':errors,'report':str(out)},indent=2),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver',choices=('peko','openclaw'),required=True)
    args=parser.parse_args()
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    raise SystemExit(0 if run(args.driver,ROOT/'reports'/f'{stamp}-compact-surface-{args.driver}')['passed'] else 1)
