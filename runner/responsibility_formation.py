#!/usr/bin/env python3
"""One compact formation-only attempt: no watch, oracle feedback or continuation."""
import argparse
import datetime as dt
import hashlib
import json
import time
from pathlib import Path
from responsibility import messages, settled_telemetry
from responsibility_drivers import PekoResponsibility, ClawResponsibility, prepared_worker_prompt
from responsibility_simulator import Simulator, load_spec
from responsibility_offline_fixture import check
from tool_surface import attribution
import responsibility_compact as compact

ROOT=Path(__file__).resolve().parent.parent


def gate(driver, workspace):
    errors=[]
    manifests=driver.metadata.get('offline_fixture_manifest',{})
    if set(manifests)!={'responsibility_offline_fixture.py','responsibility_action_service.py'}:
        errors.append('supplied fixture manifest missing')
    for name,sha in manifests.items():
        file=workspace/'.benchmark-fixture'/name
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=sha:
            errors.append('supplied offline fixture modified: '+name)
    table=json.loads((workspace/'kb/responsibility/commitments.md').read_text())
    rows={o['project']:o for o in table['obligations']}
    spec=driver.sim.spec
    for o in spec['obligations']:
        record=rows.get(o['project'],{})
        expected={k:o.get(k) for k in ('project','revision','recipient','delivery_key','deadline','blocked_at')}
        if any(record.get(k)!=v or k not in record for k,v in expected.items()):
            errors.append('canonical owner facts mismatch: '+o['project'])
        status=record.get('status')
        if (status!='cancelled' if o.get('cancelled') else status not in ('pending','blocked')):
            errors.append('pre-watch status mismatch: '+o['project'])
    if set(rows)!=set(o['project'] for o in spec['obligations']): errors.append('canonical obligation set mismatch')
    topology=driver.validate_topology('formation')
    jobs=topology['operational_jobs']
    args=['--base-url',driver.sim.url,'--workspace',str(workspace)]
    bound=False
    if len(jobs)==1:
        job=jobs[0]
        if isinstance(driver,PekoResponsibility):
            bound=(job.get('tool_name')=='Workflow' and job.get('tool_params')=={'path':'watch.py','args':args})
        else:
            payload=job.get('payload',{})
            argv=payload.get('argv',[])
            bound=(payload.get('kind')=='command' and len(argv)==6
                   and Path(argv[0]).name in ('python3','python3.12')
                   and argv[1:]==[str(workspace/'workflows/watch.py')]+args
                   and payload.get('cwd')==str(workspace))
        period=job.get('schedule',{}).get('every_ms',job.get('schedule',{}).get('everyMs'))
        bound=bound and job.get('schedule',{}).get('kind')=='every' and isinstance(period,int) and not isinstance(period,bool) and period>=5000
    if not bound: errors.append('expected one native code job bound to the validated worker and live arguments')
    if any(r['kind'] in ('action','action_attempt') for r in driver.sim.rows):
        errors.append('operational HTTP action attempted during formation')
    fixture=check(workspace/'workflows/watch.py')
    if not fixture['passed']: errors.append('trusted fictional fixture failed')
    return {'passed':not errors,'errors':errors,'canonical_requirements_verified':not any('canonical' in e or 'status' in e for e in errors),
            'native_worker_binding_verified':bound,'fixture':fixture,'native_topology':topology}


def execute(spec, driver_name, run_dir, budget=.05, timeout=900):
    run_dir.mkdir(parents=True)
    (run_dir/'scenario.json').write_text(json.dumps(spec,indent=2))
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
             for pattern in ('runner/responsibility*.py','runner/continuity*.py','runner/tool_surface.py','runner/prompt_profile.py')
             for p in ROOT.glob(pattern)}
    (run_dir/'source-manifest.json').write_text(json.dumps(sources,indent=2))
    sim=Simulator(spec,run_dir);sim.start_server()
    cls=PekoResponsibility if driver_name=='peko' else ClawResponsibility
    driver=cls(run_dir,timeout,budget,sim,'supervisory')
    errors=[];result_gate=None;telemetry={};metadata={};started=time.monotonic();phases=[];active_phase=None
    try:
        metadata=driver.start();driver.validate_topology('post-setup')
        workspace=(Path(driver.temp.name)/'.peko/principals'/driver.principal
                   if driver_name=='peko' else driver.workspace)
        sim.phase='conversation'
        for name,review,message in messages(sim):
            begin=time.monotonic();active_phase=name;sim.record('ingress',step=name,conversation='review' if review else 'owner')
            reply=driver.conversation(prepared_worker_prompt(sim)+message,review=review)
            phases.append({'phase':name,'wall_secs':round(time.monotonic()-begin,3),'completed':True})
            active_phase=None
            sim.record('reply',step=name,text=reply)
            print(f'{driver_name}: {name} acknowledged',flush=True)
        sim.phase='offline-controller-verification'
        result_gate=gate(driver,workspace)
        print(f'{driver_name}: formation gate {result_gate["passed"]}',flush=True)
    except Exception as exc:
        if active_phase:
            phases.append({'phase':active_phase,'wall_secs':round(time.monotonic()-begin,3),'completed':False})
        errors.append(f'{type(exc).__name__}: {exc}')
        print(f'{driver_name}: {errors[-1]}',flush=True)
    finally:
        sim.phase='drain'
        try: telemetry=driver.telemetry()
        except Exception as exc: errors.append(f'telemetry: {type(exc).__name__}: {exc}')
        finally:
            try: driver.close()
            except Exception as exc: errors.append(f'cleanup: {type(exc).__name__}: {exc}')
            sim.close()
            metadata=metadata|dict(driver.metadata)
            if driver.relay: telemetry=settled_telemetry(driver.relay,telemetry)
    formation_passed=bool(result_gate and result_gate['passed'] and not errors)
    if any(r['kind'] in ('action','action_attempt') for r in sim.rows):
        errors.append('operational HTTP action attempted during formation or cleanup')
        formation_passed=False
    accounting_valid=bool(telemetry.get('usage_complete') and telemetry.get('native_usage_matches'))
    result={'evidence_kind':'compact_formation_only_real_llm_attempt','formation_profile_version':compact.VERSION,
            'metadata':metadata,'errors':errors,'formation_gate':result_gate,'phases':phases,
            'usage':telemetry,'wall_secs':round(time.monotonic()-started,3),
            'tool_attribution':attribution(run_dir,driver.relay.records if driver.relay else []),
            'formation_succeeded':formation_passed,'measurement_valid':accounting_valid,
            'passed':formation_passed and accounting_valid,
            'watch_started':False,'completed_obligations':None,'missed_deadlines':None,
            'memory_accuracy':None,'restart_verified':None,'organizational_supervision_armed':False}
    (run_dir/'result.json').write_text(driver._redact(json.dumps(result,indent=2)))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver',choices=('peko','openclaw'),required=True)
    parser.add_argument('--seed',type=int,default=1)
    args=parser.parse_args()
    spec=load_spec(ROOT/'scenarios/responsibility/pilot.toml',args.seed)
    spec.update(formation_profile='compact-v1',execution_policy='strategy-choice',formation='prepared',
                topology='separated',action_mode='guarded',profile_prompt=True)
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run_dir=ROOT/'reports'/f'{stamp}-responsibility-formation-{args.driver}'
    result=execute(spec,args.driver,run_dir)
    print('report='+str(run_dir),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
