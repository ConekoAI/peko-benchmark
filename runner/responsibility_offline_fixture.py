"""Shared fictional HTTP fixture; contains no operational worker or live facts.

Usage: python responsibility_offline_fixture.py /absolute/workflows/watch.py
Worker interface: SCRIPT --base-url URL --workspace DIR (stdlib Python only).
"""
import argparse
import copy
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from responsibility_action_service import ActionService

VERSION = 1
CASES = ('inactive', 'not_ready', 'wrong_revision', 'cancelled', 'past_deadline', 'accepted_and_quiet',
         'rejected', 'reconcile_committed', 'uncertain_write', 'blocked_threshold')


def run_case(script, name):
    with tempfile.TemporaryDirectory(prefix='responsibility-offline-') as folder:
        workspace = Path(folder)
        notes = workspace / 'kb/responsibility'; notes.mkdir(parents=True)
        obligation = {'project':'fictional-alpha', 'revision':'r2', 'recipient':'fictional-room',
                      'delivery_key':'fictional-key', 'deadline':30, 'blocked_at':None, 'status':'pending'}
        state = {'watch_active':True, 'elapsed_secs':5, 'duration_secs':40, 'world_version':1,
                 'dependencies':{obligation['project']:{'ready':True,'revision':'r2'}}}
        if name == 'inactive': state['watch_active'] = False
        if name == 'not_ready': state['dependencies'][obligation['project']]['ready'] = False
        if name == 'wrong_revision': state['dependencies'][obligation['project']]['revision'] = 'r1'
        if name == 'cancelled': obligation['status'] = 'cancelled'
        if name == 'past_deadline': state['elapsed_secs'] = 31
        if name == 'blocked_threshold':
            obligation['blocked_at'] = 10
            state['elapsed_secs'] = 9
            state['dependencies'][obligation['project']]['ready'] = False
        commitments = notes/'commitments.md'
        commitments.write_text(json.dumps({'obligations':[obligation]}))
        receipts = notes/'receipts.md'; receipts.write_text('')
        service = ActionService(workspace/'effects.sqlite')
        action = {k:obligation[k] for k in ('project','revision','recipient','delivery_key')}
        action['kind'] = 'send_release'
        envelope = {'action':action, 'preconditions':{'watch_active':True,
                    'dependency':{'ready':True,'revision':'r2'}}}
        if name == 'reconcile_committed': service.submit(envelope, state)
        attempts, reads, dropped = [], [], []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def reply(self, status, value):
                body=json.dumps(value).encode()
                self.send_response(status); self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_GET(self):
                reads.append(self.path)
                if self.path == '/world': self.reply(200,copy.deepcopy(state))
                elif self.path == '/receipts': self.reply(200,{'receipts':service.receipts()})
                else: self.reply(404,{'error':'unknown fixture path'})
            def do_POST(self):
                if self.path != '/actions': return self.reply(404,{'error':'unknown fixture path'})
                value=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
                attempts.append(value)
                if name == 'rejected':
                    return self.reply(412,{'accepted':False,'effect_applied':False,'error':'fixture dependency changed'})
                status,response=service.submit(value,state)
                if name == 'uncertain_write' and response.get('effect_applied') and not dropped:
                    dropped.append(True); self.close_connection=True
                    self.connection.shutdown(socket.SHUT_RDWR); self.connection.close(); return
                self.reply(status,response)

        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        env={k:v for k,v in os.environ.items() if k in ('PATH','SYSTEMROOT','TMPDIR','LANG')}
        env['PEKO_WORKSPACE']=str(workspace)
        invocations=[]
        def invoke(allow_failure=False):
            result=subprocess.run([sys.executable,str(script),'--base-url',url,'--workspace',str(workspace)],
                                  cwd=workspace,env=env,capture_output=True,text=True,timeout=8)
            invocations.append({'returncode':result.returncode,'stderr_tail':result.stderr[-800:]})
            if not allow_failure: assert result.returncode == 0, 'worker exited with an error'
        def table(): return json.loads(commitments.read_text())['obligations'][0]
        try:
            before=(commitments.read_bytes(),receipts.read_bytes())
            invoke(allow_failure=name=='uncertain_write')
            if name in ('inactive','not_ready','wrong_revision','cancelled','past_deadline'):
                assert not attempts and not service.receipts(), 'ineligible work produced an action'
                assert before==(commitments.read_bytes(),receipts.read_bytes()), 'quiet invocation rewrote notes'
            elif name == 'rejected':
                assert attempts and not service.receipts(), 'rejection case was not exercised correctly'
                assert table()['status']=='pending', 'rejected delivery became delivered'
            elif name == 'blocked_threshold':
                assert not attempts, 'request_input happened before the retained threshold'
                state['elapsed_secs']=12; invoke()
                committed=service.receipts()
                assert len(committed)==1 and committed[0]['action']['kind']=='request_input', 'blocked input missing'
                assert table()['status']=='blocked', 'request_input did not retain blocked state'
                before=(commitments.read_bytes(),receipts.read_bytes()); count=len(attempts); invoke()
                assert len(attempts)==count and before==(commitments.read_bytes(),receipts.read_bytes()), 'unchanged blocked work repeated'
            else:
                if name == 'uncertain_write': invoke()
                committed=service.receipts()
                assert len(committed)==1 and committed[0]['action']==action, 'matching release receipt missing'
                assert table()['status']=='delivered', 'accepted/reconciled delivery remains pending'
                assert str(committed[0]['receipt']) in receipts.read_text(), 'actual receipt number not retained'
                if name in ('uncertain_write','reconcile_committed'):
                    assert '/receipts' in reads, 'uncertain/precommitted result was not reconciled'
                before=(commitments.read_bytes(),receipts.read_bytes()); count=len(attempts); invoke()
                assert len(attempts)==count and before==(commitments.read_bytes(),receipts.read_bytes()), 'unchanged delivered work repeated'
            return {'case':name,'passed':True,'invocations':invocations,'attempts':len(attempts)}
        except (AssertionError,ValueError,KeyError,subprocess.TimeoutExpired) as exc:
            return {'case':name,'passed':False,'error':str(exc),'invocations':invocations,'attempts':len(attempts)}
        finally:
            server.shutdown();server.server_close();thread.join(2)


def check(script):
    script=Path(script).resolve(strict=True)
    cases=[run_case(script,name) for name in CASES]
    return {'fixture_version':VERSION,'fictional_only':True,'passed':all(c['passed'] for c in cases),'cases':cases}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('script',type=Path)
    result=check(parser.parse_args().script)
    print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
