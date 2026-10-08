#!/usr/bin/env python3
"""Scripted Anthropic responses through real native harnesses, with zero LLM calls.

This tests decoding, dispatch and path reachability, not model competence. Every
response is controller-scripted. It never shares scores with live pilots.
"""
import argparse
import hashlib
import datetime as dt
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from continuity_peko import PekoDriver
from continuity_openclaw import OpenClawDriver, final_reply
from responsibility_simulator import Simulator, load_spec
from tool_surface import catalog, tool_call

ROOT = Path(__file__).resolve().parent.parent


class ScriptedProvider:
    def __init__(self):
        self.steps, self.calls, self.results, self.catalogs = [], [], {}, []
        self.stop_reasons = []  # Optional scripted terminal reason, never live-provider feedback.
        self.lock = threading.Lock()
        provider = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with provider.lock:
                    tools = catalog(payload)
                    provider.catalogs.append(tools)
                    for message in payload.get('messages', []):
                        for block in message.get('content', []) if isinstance(message.get('content'), list) else []:
                            if block.get('type') == 'tool_result':
                                provider.results[block['tool_use_id']] = block
                    if provider.steps:
                        name, args = provider.steps.pop(0)
                        block = {'type': 'tool_use', 'id': f'surface{len(provider.calls)+1}',
                                 'name': name, 'input': args}
                        provider.calls.append(tool_call(block, tools))
                    else:
                        block = {'type': 'text', 'text': 'SURFACE_ACK'}
                message = {'id': 'msg_surface', 'type': 'message', 'role': 'assistant',
                           'model': payload['model'], 'content': [block],
                           'stop_reason': 'tool_use' if block['type'] == 'tool_use' else 'end_turn',
                           'stop_sequence': None, 'usage': {'input_tokens': 10, 'output_tokens': 5}}
                if provider.stop_reasons:
                    message['stop_reason'] = provider.stop_reasons.pop(0)
                if payload.get('stream'):
                    start = dict(message, content=[], stop_reason=None)
                    initial = dict(block, input={}) if block['type'] == 'tool_use' else dict(block, text='')
                    delta = ({'type': 'input_json_delta', 'partial_json': json.dumps(block['input'])}
                             if block['type'] == 'tool_use' else {'type': 'text_delta', 'text': block['text']})
                    events = [{'type': 'message_start', 'message': start},
                              {'type': 'content_block_start', 'index': 0, 'content_block': initial},
                              {'type': 'content_block_delta', 'index': 0, 'delta': delta},
                              {'type': 'content_block_stop', 'index': 0},
                              {'type': 'message_delta', 'delta': {'stop_reason': message['stop_reason'],
                                                               'stop_sequence': None}, 'usage': {'output_tokens': 5}},
                              {'type': 'message_stop'}]
                    data = ''.join(f'event: {e["type"]}\ndata: {json.dumps(e)}\n\n' for e in events).encode()
                    content_type = 'text/event-stream'
                else:
                    data, content_type = json.dumps(message).encode(), 'application/json'
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)


class SmokeClaw(OpenClawDriver):
    def configure(self, config):
        config['agents']['defaults']['heartbeat'] = {'every': '0m'}
        config['tools'] = {'exec': {'host': 'gateway', 'security': 'full', 'ask': 'off'}}


def run(driver_name, out):
    out.mkdir(parents=True)
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
             for pattern in ("runner/responsibility*.py","runner/continuity*.py","runner/tool_surface.py")
             for p in ROOT.glob(pattern)}
    (out/"source-manifest.json").write_text(json.dumps(sources,indent=2))
    provider = ScriptedProvider()
    os.environ.update(PEKO_API_KEY='scripted-no-real-key', PEKO_BASE_URL=provider.url,
                      PEKO_MODEL_NAME='mimo-v2.6-flash', PEKO_MODEL_ID='mimo-v2.6-flash',
                      PEKO_API_FORMAT='anthropic_messages', PEKO_CONTEXT_WINDOW='1048576',
                      PEKO_MAX_OUTPUT_TOKENS='4096', PEKO_MODEL_SPEC=json.dumps({
                          'tool_support':'function_calling', 'streaming':True, 'thinking':'optional',
                          'pricing':{'input_per_million': .14, 'output_per_million': .28}}))
    driver = (PekoDriver if driver_name == 'peko' else SmokeClaw)(out, 240, .1)
    sim = Simulator(load_spec(ROOT/'scenarios/responsibility/pilot.toml', 1), out)
    url = sim.start_server()
    checks, error = [], None
    try:
        metadata = driver.start()
        if driver_name == 'peko':
            workspace = Path(driver.temp.name)/'.peko/principals'/driver.principal
            read, write, edit, shell = 'Read', 'Write', 'Edit', 'Bash'
            file_field, content_field, old_field, new_field = 'file_path', 'content', 'old_string', 'new_string'
        else:
            workspace = driver.workspace
            (workspace/'BOOTSTRAP.md').unlink(missing_ok=True)
            read, write, edit, shell = 'read', 'write', 'edit', 'exec'
            file_field, content_field, old_field, new_field = 'path', 'content', 'oldText', 'newText'
        target = workspace/'kb/responsibility/surface.txt'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('SURFACE_INITIAL')
        plans = [('absolute-read', read, {file_field:str(target)}, 'SURFACE_INITIAL', False),
                 ('relative-read', read, {file_field:'kb/responsibility/surface.txt'}, 'SURFACE_INITIAL', driver_name=='peko'),
                 ('write', write, {file_field:str(target),content_field:'SURFACE_WRITTEN'}, None, False),
                 ('edit', edit, ({file_field:str(target),old_field:'SURFACE_WRITTEN',new_field:'SURFACE_EDITED'} if driver_name=='peko' else
                                {'path':str(target),'edits':[{'oldText':'SURFACE_WRITTEN','newText':'SURFACE_EDITED'}]}), None,False),
                 ('read-after-edit',read,{file_field:str(target)},'SURFACE_EDITED',False),
                 ('cwd',shell,{'command':'pwd'}, str(workspace.resolve()) if driver_name=='openclaw' else '/workspaces',False),
                 ('world-get',shell,{'command':f'curl -sS --max-time 10 {url}/world'},'watch_active',False),
                 ('action-post',shell,{'command':f"curl -sS --max-time 10 -H 'Content-Type: application/json' --data '{{\"kind\":\"surface_probe\"}}' {url}/actions"},'receipt',False)]
        for label, name, args, expected, expected_error in plans:
            provider.steps.append((name,args))
            driver.turn('SCRIPTED_SURFACE_PROBE: execute only the provided tool call then acknowledge.')
            call = provider.calls[-1]
            result = provider.results.get(call['id'])
            result_text = json.dumps(result.get('content')) if result else ''
            is_error = result.get('is_error',False) if result else None
            passed = (bool(result) and call['advertised'] and not call['missing_required']
                      and is_error == expected_error and (expected is None or expected in result_text or expected_error))
            checks.append({'check':label, 'wire_tool':call, 'native_result_error':is_error,
                           'expected_error':expected_error, 'expected_content_found':expected is None or expected in result_text,
                           'passed':passed})
        if driver_name=='peko':
            # Production Agent tool -> persistent child -> same native file/shell dispatcher.
            role=workspace/'roles/surface-worker.md'
            role.parent.mkdir(parents=True,exist_ok=True)
            role.write_text('---\nname: surface-worker\n---\nExecute supplied probes, then finish.')
            provider.steps.extend([('Agent',{'action':'new','path':'/surface-worker','role':'surface-worker',
                                             'prompt':'SCRIPTED_SURFACE_WORKER: run the supplied probes then finish.',
                                             'timeout_secs':30}),
                                   (read,{file_field:str(target)}),
                                   (shell,{'command':f'curl -sS --max-time 10 {url}/world'})])
            driver.turn('SCRIPTED_SURFACE_PROBE: run the supplied persistent child probe.')
            nested=provider.calls[-3:]
            checks.append({'check':'persistent-child-dispatch', 'passed':all(
                c['id'] in provider.results and not provider.results[c['id']].get('is_error',False)
                for c in nested), 'wire_tools':nested})
        else:
            provider.steps.extend([(read,{file_field:str(target)}),
                                   (shell,{'command':f'curl -sS --max-time 10 {url}/world'})])
            final_reply(json.loads(driver._command('agent','--session-key','agent:main:release-watch',
                                                   '--message','SCRIPTED_SURFACE_WORKER','--json')))
            nested=provider.calls[-2:]
            checks.append({'check':'persistent-worker-dispatch','passed':all(
                c['id'] in provider.results and not provider.results[c['id']].get('is_error',False)
                for c in nested),'wire_tools':nested})
        guard_dir=out/'guarded';guard_dir.mkdir()
        guard_spec=load_spec(ROOT/'scenarios/responsibility/pilot.toml',1);guard_spec['action_mode']='guarded'
        clock=[0];guard=Simulator(guard_spec,guard_dir,lambda:clock[0]);guard_url=guard.start_server();guard.begin();clock[0]=90
        a=guard_spec['obligations'][0]
        envelope={'action':{'kind':'send_release',**{k:a[k] for k in ('project','revision','recipient','delivery_key')}},
                  'preconditions':{'watch_active':True,'dependency':{'ready':True,'revision':'r2'}}}
        try:
            for label,payload,expected in [('guard-commit',envelope,'"effect_applied": true'),
                                           ('guard-replay',envelope,'"replayed": true'),
                                           ('guard-conflict',dict(envelope,action=dict(envelope['action'],recipient='other')),'409'),
                                           ('guard-rejected-precondition',{'action':{'kind':'request_input','project':guard_spec['obligations'][3]['project'],'reason':'dependency_blocked'},'preconditions':{'watch_active':True,'dependency':{'ready':False,'revision':'r1'},'not_before':180}},'412')]:
                command=(f"curl -sS --max-time 10 -w ' HTTP=%{{http_code}}' -H 'Content-Type: application/json' "
                         f"--data '{json.dumps(payload)}' {guard_url}/actions")
                provider.steps.append((shell,{'command':command}))
                driver.turn('SCRIPTED_ACTION_SERVICE_PROBE')
                call=provider.calls[-1];result=provider.results.get(call['id'],{})
                # Decode tool-result text instead of matching JSON-escaped HTTP content.
                text=' '.join(b.get('text','') for b in result.get('content',[]) if isinstance(b,dict)) if isinstance(result.get('content'),list) else str(result.get('content'))
                if driver_name=='peko':text=json.loads(text).get('stdout','')
                checks.append({'check':label,'passed':bool(result) and expected in text and not result.get('is_error',False), 'wire_tool':call})
            provider.steps.append((shell,{'command':f'curl -sS --max-time 10 {guard_url}/receipts'}))
            driver.turn('SCRIPTED_ACTION_SERVICE_RECEIPT_LOOKUP')
            call=provider.calls[-1];result=provider.results.get(call['id'],{})
            checks.append({'check':'durable-receipt-lookup','passed':'committed_elapsed_secs' in str(result) and len(guard.action_service.receipts())==1})
        finally:
            guard.close()
        telemetry = driver.telemetry()
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
        metadata, telemetry = driver.metadata, {}
    finally:
        driver.close(); sim.close(); provider.close()
    if not error:
        scope={}
        for path in (out/'runtime-traces').rglob('*.jsonl'):
            for line in path.read_text().splitlines():
                row=json.loads(line)
                if not isinstance(row,dict):continue
                event=row.get('event',row)
                if not isinstance(event,dict):continue
                message=event.get('message',event)
                if not isinstance(message,dict):continue
                for block in message.get('content',[]) if isinstance(message.get('content'),list) else []:
                    if block.get('type') in ('tool_call','toolCall'):
                        scope[block.get('id')]=row.get('session_id',path.stem)
        root_scope=scope.get(provider.calls[0]['id'])
        proof=next(c for c in checks if c['check'] in ('persistent-child-dispatch','persistent-worker-dispatch'))
        worker_calls=proof['wire_tools'][1:] if driver_name=='peko' else proof['wire_tools']
        worker_scopes={scope.get(c['id']) for c in worker_calls}
        proof['distinct_worker_session_verified']=len(worker_scopes)==1 and None not in worker_scopes and root_scope not in worker_scopes
        proof['passed']=proof['passed'] and proof['distinct_worker_session_verified']
    result={'evidence_kind' :'scripted_provider_native_surface_smoke', 'driver':driver_name,
            'real_llm_calls':0,'metadata':metadata,'checks':checks,'error':error,
            'passed':bool(checks) and all(c['passed'] for c in checks) and error is None,
            'catalogs':provider.catalogs,'usage':telemetry,
            'limits':'Not evidence of model competence or unattended cadence/recovery. Relative Peko path failure is expected and must be accounted for in prompts.'}
    (out/'surface-result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:result[k] for k in ('driver','passed','error','checks')},indent=2),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver',choices=('peko','openclaw'),required=True)
    args=parser.parse_args()
    name=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-surface-'+args.driver
    result=run(args.driver,ROOT/'reports'/name)
    raise SystemExit(0 if result['passed'] else 1)
