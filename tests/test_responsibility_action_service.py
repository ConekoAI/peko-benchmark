import copy
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'runner'))
from responsibility_action_service import ActionService
from responsibility_simulator import Simulator, load_spec, score


class ActionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'effects.sqlite'
        self.service=ActionService(self.path)
        self.state={'watch_active':True,'elapsed_secs':100,'dependencies':{'a':{'ready':True,'revision':'r2'},'d':{'ready':False,'revision':'r1'}}}
        self.envelope={'action':{'kind':'send_release','project':'a','revision':'r2','recipient':'room','delivery_key':'k'},
                       'preconditions':{'watch_active':True,'dependency':{'ready':True,'revision':'r2'}}}

    def tearDown(self): self.temp.cleanup()

    def test_receipt_survives_restart_and_retry_does_not_duplicate_effect(self):
        status, first=self.service.submit(self.envelope,self.state)
        self.assertEqual(status,200);self.assertTrue(first['effect_applied'])
        restarted=ActionService(self.path)
        # A committed retry is evidence lookup even after watch ends.
        status, retry=restarted.submit(self.envelope,self.state|{'watch_active':False})
        self.assertEqual(status,200);self.assertEqual(retry['receipt'],first['receipt'])
        self.assertTrue(retry['replayed']);self.assertFalse(retry['effect_applied'])
        self.assertEqual(len(restarted.receipts()),1)

    def test_concurrent_retries_commit_one_effect(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            replies=list(pool.map(lambda _:self.service.submit(self.envelope,self.state),range(12)))
        self.assertEqual(sum(r['effect_applied'] for _,r in replies),1)
        self.assertEqual(len({r['receipt'] for _,r in replies}),1)

    def test_conflicting_payload_cannot_overwrite_committed_receipt(self):
        self.service.submit(self.envelope,self.state)
        other=copy.deepcopy(self.envelope);other['action']['recipient']='other'
        status,response=self.service.submit(other,self.state)
        self.assertEqual(status,409);self.assertFalse(response['effect_applied'])
        self.assertEqual(self.service.receipts()[0]['action']['recipient'],'room')

    def test_preconditions_and_schema_fail_without_effect_or_future_oracle(self):
        for mutation,status in [('not-ready',412),('wrong-revision',412),('inactive',412),('missing-schema',400)]:
            state=copy.deepcopy(self.state);env=copy.deepcopy(self.envelope)
            if mutation=='not-ready': state['dependencies']['a']['ready']=False
            if mutation=='wrong-revision': state['dependencies']['a']['revision']='r3'
            if mutation=='inactive':state['watch_active']=False
            if mutation=='missing-schema':del env['preconditions']
            self.assertEqual(self.service.submit(env,state)[0],status)
        self.assertEqual(self.service.receipts(),[])

    def test_blocked_threshold_is_callers_policy_not_hidden_answer(self):
        env={'action':{'kind':'request_input','project':'d','reason':'dependency_blocked'},
             'preconditions':{'watch_active':True,'dependency':{'ready':False,'revision':'r1'},'not_before':180}}
        self.assertEqual(self.service.submit(env,self.state)[0],412)
        self.assertEqual(self.service.submit(env,self.state|{'elapsed_secs':180})[0],200)
        for value in (True,float('inf'),-1,'180'):
            env['preconditions']['not_before']=value
            self.assertEqual(self.service.submit(env,self.state)[0],400)
        # Wrong owner threshold is a policy failure, not silently prevented by oracle.
        env['action']['project']='other';env['preconditions']['not_before']=0
        state=self.state|{'dependencies':{'other':{'ready':False,'revision':'r1'}}}
        self.assertEqual(self.service.submit(env,state)[0],200)

    def test_simulator_scores_effects_and_retains_rejected_and_replayed_attempts(self):
        spec=load_spec(ROOT/'scenarios/responsibility/pilot.toml',1);spec['action_mode']='guarded'
        now=[0];sim=Simulator(spec,Path(self.temp.name),lambda:now[0]);sim.begin()
        a=spec['obligations'][0]
        env={'action':{'kind':'send_release',**{k:a[k] for k in ('project','revision','recipient','delivery_key')}},
             'preconditions':{'watch_active':True,'dependency':{'ready':True,'revision':'r2'}}}
        self.assertEqual(sim.guarded_submit(env)[0],412)
        now[0]=90
        self.assertEqual(sim.guarded_submit(env)[0],200)
        self.assertTrue(sim.guarded_submit(env)[1]['replayed'])
        self.assertEqual(len([r for r in sim.rows if r['kind']=='action_attempt']),3)
        self.assertEqual(len([r for r in sim.rows if r['kind']=='action']),1)
        self.assertEqual(score(spec,sim.rows,{},False)['completed_obligations'],1)
