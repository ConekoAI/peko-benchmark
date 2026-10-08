import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'runner'))
import responsibility_compact as compact
from responsibility_offline_fixture import check
from responsibility_formation import gate
from responsibility_compact_smoke import fixture_passed
from types import SimpleNamespace
from unittest.mock import patch

# Fixture certification only. Never provisioned into a native agent workspace.
REFERENCE = '''
import argparse,json,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--workspace');a=p.parse_args()
folder=Path(a.workspace)/'kb/responsibility';table=folder/'commitments.md';log=folder/'receipts.md'
def get(path):
    return json.load(urllib.request.urlopen(a.base_url+path,timeout=2))
world=get('/world')
if not world['watch_active']: raise SystemExit(0)
data=json.loads(table.read_text());existing=get('/receipts')['receipts'];changed=False
for o in data['obligations']:
    if o['status']=='cancelled': continue
    found=next((r for r in existing if r['action']['project']==o['project']),None)
    if found:
        status='delivered' if found['action']['kind']=='send_release' else 'blocked'
        if o['status']!=status:
            o['status']=status;changed=True
            with log.open('a') as f: f.write(json.dumps(found)+'\\n')
        continue
    dep=world['dependencies'][o['project']];elapsed=world['elapsed_secs']
    if o['deadline'] is not None and elapsed>o['deadline']: continue
    if dep['ready'] and dep['revision']==o['revision']:
        action={k:o[k] for k in ('project','revision','recipient','delivery_key')};action['kind']='send_release'
        pre={'watch_active':True,'dependency':dep}
    elif not dep['ready'] and o['blocked_at'] is not None and elapsed>=o['blocked_at']:
        action={'kind':'request_input','project':o['project'],'reason':'dependency_blocked'}
        pre={'watch_active':True,'dependency':dep,'not_before':o['blocked_at']}
    else: continue
    body=json.dumps({'action':action,'preconditions':pre}).encode()
    try:
        req=urllib.request.Request(a.base_url+'/actions',data=body,headers={'Content-Type':'application/json'})
        response=json.load(urllib.request.urlopen(req,timeout=2))
    except urllib.error.HTTPError: continue
    if response.get('accepted'):
        o['status']='delivered' if action['kind']=='send_release' else 'blocked';changed=True
        with log.open('a') as f: f.write(json.dumps(response)+'\\n')
if changed: table.write_text(json.dumps(data))
'''


class CompactTests(unittest.TestCase):
    def test_native_fixture_result_decodes_nested_tool_content(self):
        good=json.dumps({'fixture_version':1,'passed':True})
        self.assertTrue(fixture_passed({'content':json.dumps({'stdout':good,'exit_code':0})}))
        self.assertTrue(fixture_passed({'content':[{'type':'text','text':good}]}))
        self.assertFalse(fixture_passed({'content':json.dumps({'fixture_version':1,'passed':False})}))
        self.assertFalse(fixture_passed({'passed':True}))

    def test_shared_http_fixture_accepts_valid_worker_and_rejects_noop(self):
        with tempfile.TemporaryDirectory() as folder:
            script=Path(folder)/'worker.py';script.write_text(REFERENCE)
            result=check(script)
            self.assertTrue(result['passed'],json.dumps(result))
            self.assertEqual(len(result['cases']),10)
            script.write_text('pass')
            failed=check(script)
            self.assertFalse(failed['passed'])
            self.assertTrue(any(not r['passed'] and r['case']=='accepted_and_quiet' for r in failed['cases']))

    def test_provision_supplies_mock_only_not_a_worker_or_live_facts(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest=compact.provision(folder)
            self.assertEqual(set(manifest),{'responsibility_offline_fixture.py','responsibility_action_service.py'})
            self.assertFalse((Path(folder)/'workflows/watch.py').exists())
            self.assertFalse((Path(folder)/'kb/responsibility/commitments.md').exists())
            prompt=compact.contract('http://127.0.0.1:1')
            self.assertIn('do not rebuild healthy code or tests',prompt)
            self.assertNotIn('Atlas',prompt)

    def test_native_capability_examples_use_valid_json_and_live_arguments(self):
        prompt=compact.capabilities('peko',Path('/tmp/workspace'),url='http://127.0.0.1:1')
        params=prompt.split('params=',1)[1].split(' interval_ms=',1)[0]
        self.assertEqual(json.loads(params),{'path':'watch.py','args':['--base-url','http://127.0.0.1:1','--workspace','/tmp/workspace']})
        claw=compact.capabilities('openclaw',Path('/tmp/work space'),node='/tmp/node bin',entry='/tmp/claw cli.mjs',url='http://127.0.0.1:1')
        command=claw.split('automations add',1)[1].split('. automations list',1)[0]
        words=shlex.split(command)
        self.assertEqual(json.loads(words[words.index('--command-argv')+1]),
            ['python3','/tmp/work space/workflows/watch.py','--base-url','http://127.0.0.1:1','--workspace','/tmp/work space'])
        self.assertEqual(words[words.index('--command-cwd')+1],'/tmp/work space')

    def test_formation_gate_rejects_wrong_executable_and_tampered_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            workspace=Path(folder);manifest=compact.provision(workspace)
            notes=workspace/'kb/responsibility';notes.mkdir(parents=True)
            o={'project':'fictional-alpha','revision':'r2','recipient':'room','delivery_key':'key',
               'deadline':30,'blocked_at':None,'status':'pending'}
            (notes/'commitments.md').write_text(json.dumps({'obligations':[o]}))
            job={'schedule':{'kind':'every','everyMs':10000},'payload':{'kind':'command','cwd':folder,
                 'argv':['python3',str(workspace/'workflows/watch.py'),'--base-url','http://127.0.0.1:1','--workspace',folder]}}
            driver=SimpleNamespace(metadata={'offline_fixture_manifest':manifest},
                sim=SimpleNamespace(url='http://127.0.0.1:1',spec={'obligations':[o]},rows=[]),
                validate_topology=lambda stage:{'operational_jobs':[job]})
            with patch('responsibility_formation.check',return_value={'passed':True}):
                self.assertTrue(gate(driver,workspace)['passed'])
                job['payload']['argv'][0]='echo'
                self.assertFalse(gate(driver,workspace)['native_worker_binding_verified'])
                job['payload']['argv'][0]='python3'
                (workspace/'.benchmark-fixture/responsibility_offline_fixture.py').write_text('pass')
                self.assertFalse(gate(driver,workspace)['passed'])


if __name__=='__main__':unittest.main()
