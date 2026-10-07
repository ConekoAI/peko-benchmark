import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'runner'))
import responsibility_strategy as strategy
from responsibility import contract
from responsibility_prepared import arm_peko, pause_claw_for_probe, empty_notes, set_claw_due_times
from responsibility_drivers import prepared_worker_prompt


class StrategyTests(unittest.TestCase):
    def test_claw_arm_waits_for_native_heartbeat_reconciliation(self):
        pages = iter([{'jobs':[]}, {'jobs':[{'enabled':True,'payload':{'kind':'heartbeat'},
                                          'schedule':{'everyMs':120000}}]}])
        commands = []
        def command(*args):
            commands.append(args)
            return json.dumps(next(pages)) if args[0] == 'automations' else ''
        driver = SimpleNamespace(sim=SimpleNamespace(spec={'execution_policy':'strategy-choice','cadence_secs':60}),
            _command=command, _stop_gateway=lambda:None, _start_gateway=lambda:None)
        with patch('responsibility_prepared.time.sleep') as sleep:
            set_claw_due_times(driver, armed=True)
        self.assertEqual(sleep.call_count, 1)
        self.assertFalse(any(c[:2] == ('gateway','call') for c in commands))
        driver._command = lambda *args: json.dumps({'jobs':[]})
        with patch('responsibility_prepared.time.monotonic', side_effect=[0,21]):
            with self.assertRaises(TimeoutError):
                set_claw_due_times(driver, armed=True)

    def test_claw_native_history_paginates_and_refuses_nonadvancing_cursor(self):
        pages = iter([{'entries':[{'runId':'one'}], 'hasMore':True, 'nextOffset':200},
                      {'entries':[{'runId':'two'}], 'hasMore':False}])
        driver = SimpleNamespace(_command=lambda *args:json.dumps(next(pages)))
        value = strategy.claw_runs(driver)
        self.assertEqual(value['page_count'], 2)
        self.assertEqual(len(value['entries']), 2)
        driver = SimpleNamespace(_command=lambda *args:json.dumps({'entries':[], 'hasMore':True,'nextOffset':0}))
        with self.assertRaises(ValueError):
            strategy.claw_runs(driver)

    def test_track_opt_in_and_shared_prompts_do_not_prescribe_fixed_worker(self):
        spec = {'execution_policy': 'strategy-choice', 'cadence_secs': 60, 'duration_secs': 300}
        sim = SimpleNamespace(spec=spec, url='http://127.0.0.1:1234', action_service=None)
        prompt = contract(sim)
        self.assertTrue(strategy.selected(spec))
        self.assertFalse(strategy.selected({}))
        for fragment in ('native recurring code jobs', 'one-shot tool/code jobs', 'entire LLM/tool sequence',
                         'never lower a threshold', 'Serialize operational effects', 'five seconds'):
            self.assertIn(fragment, prompt)
        for fragment in ('Do not add other monitors', 'Make at most one GET', 'no extra timers',
                         'cedar', 'dogwood', 'r1', '180s', '240s'):
            self.assertNotIn(fragment, prompt)
        self.assertEqual(prepared_worker_prompt(sim), prompt)

    def test_empty_fixture_has_no_operational_solution_and_no_conflicting_fixed_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            empty_notes(workspace, 'CHOOSE_STRATEGY', strategy=True)
            self.assertEqual(list(workspace.rglob('*.py')), [])
            self.assertIn('No commitments received', (workspace/'kb/responsibility/commitments.md').read_text())
            prompt = (workspace/'RESPONSIBILITY.md').read_text()
            self.assertIn('create or update the task automation', prompt)
            self.assertNotIn('registered native worker', prompt)

    def test_strategy_registration_accepts_native_code_and_one_shots(self):
        supervisor = {'id':'sup', 'name':'organization-supervisor', 'enabled':True, 'kind':'send',
                      'schedule':{'every_ms':120000}}
        worker = {'id':'code', 'enabled':True, 'kind':'spawn_tool', 'tool_name':'Workflow',
                  'schedule':{'kind':'at', 'at':'2099-01-01T00:00:00Z'}}
        sessions = {'trunk':{'session_id':'trunk', 'parent_session_id':None}}
        self.assertTrue(strategy.verify('peko', {'jobs':[supervisor]}, sessions, 60, 'post-setup')['verified'])
        self.assertFalse(strategy.verify('peko', {'jobs':[supervisor]}, sessions, 60, 'pre-watch')['verified'])
        self.assertTrue(strategy.verify('peko', {'jobs':[supervisor,worker]}, sessions, 60, 'pre-watch')['verified'])
        self.assertTrue(strategy.verify('peko', {'jobs':[supervisor]}, sessions, 60, 'post-watch')['verified'])
        worker['schedule'] = {'every_ms':1000}
        self.assertFalse(strategy.verify('peko', {'jobs':[supervisor,worker]}, sessions, 60, 'pre-watch')['verified'])
        heartbeat = {'id':'sup', 'enabled':True,'payload':{'kind':'heartbeat'},'schedule':{'everyMs':120000}}
        command = {'id':'command','enabled':True,'payload':{'kind':'command'},'delivery':{'mode':'none'},'schedule':{'everyMs':5000}}
        self.assertTrue(strategy.verify('openclaw', {'jobs':[heartbeat,command]}, {}, 60, 'pre-watch')['verified'])
        command['delivery']['mode'] = 'announce'
        self.assertFalse(strategy.verify('openclaw', {'jobs':[heartbeat,command]}, {}, 60, 'pre-watch')['verified'])

    def test_arming_preserves_model_selected_operational_anchors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'.peko/data/principals/bench/local/cron'
            root.mkdir(parents=True)
            path = root/'schedule.toml'
            path.write_text(json.dumps({'jobs':[{'name':'organization-supervisor','next_run':'old'},
                {'name':'chosen-code','next_run':'MODEL_CHOSEN_ANCHOR'}]}))
            driver = SimpleNamespace(temp=SimpleNamespace(name=temp), principal='bench',
                sim=SimpleNamespace(spec={'execution_policy':'strategy-choice','cadence_secs':60}),
                _stop_owned_daemon=lambda:None, _command=lambda *args:None, _ready=lambda:None)
            arm_peko(driver)
            jobs = json.loads(path.read_text())['jobs']
            self.assertNotEqual(jobs[0]['next_run'], 'old')
            self.assertEqual(jobs[1]['next_run'], 'MODEL_CHOSEN_ANCHOR')

    def test_probe_suspends_every_model_owned_job_not_only_old_monitor_name(self):
        commands = []
        jobs = [{'id':'chosen-code','payload':{'kind':'command'}},
                {'id':'oneshot','payload':{'kind':'agentTurn'}},
                {'id':'heartbeat','payload':{'kind':'heartbeat'}},
                {'id':'internal','declarationKey':'memory-core:x'}]
        driver = SimpleNamespace(sim=SimpleNamespace(spec={'execution_policy':'strategy-choice'}), metadata={},
            _command=lambda *args: commands.append(args) or json.dumps({'jobs':jobs}),
            _stop_gateway=lambda:None, _start_gateway=lambda:None)
        pause_claw_for_probe(driver)
        disabled = [c[2] for c in commands if c[:2] == ('automations','edit')]
        self.assertEqual(disabled, ['chosen-code','oneshot'])

    def test_code_presence_and_registration_cannot_certify_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'topology-pre-watch.json').write_text(json.dumps({'schedule':{'jobs':[
                {'id':'sup','name':'organization-supervisor'}, {'id':'code'}]},
                'check':{'operational_jobs':[{'id':'code'}]}}))
            self.assertFalse(strategy.execution_evidence(root, 100, 200)['verified'])
            (root/'strategy-native-runs.json').write_text(json.dumps({'entries':[
                {'jobId':'code','runId':'a','action':'finished','status':'ok','runAtMs':150000,'durationMs':50},
                {'jobId':'code','runId':'b','action':'finished','status':'ok','runAtMs':99000}]}))
            # Native timestamps are milliseconds, including fixtures below Unix's usual magnitude.
            result = strategy.execution_evidence(root, 100, 200)
            self.assertTrue(result['verified'])
            self.assertEqual(len(result['operational_completed_runs']), 1)

    def test_artifacts_exclude_sdk_and_vault_and_redact_execution_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)/'workspace'; workspace.mkdir()
            (workspace/'workflows').mkdir()
            (workspace/'workflows/chosen.py').write_text('TOKEN_SENTINEL')
            (workspace/'.benchmark-sdk').mkdir()
            (workspace/'.benchmark-sdk/client.py').write_text('not authored')
            (workspace/'credentials').mkdir()
            (workspace/'credentials/vault.json').write_text('SECRET')
            out = Path(temp)/'out'; out.mkdir()
            files = strategy.retain_artifacts(SimpleNamespace(run_dir=out,
                _redact=lambda text:text.replace('TOKEN_SENTINEL','[REDACTED]')),workspace)
            self.assertEqual([f['path'] for f in files], ['workflows/chosen.py'])
            self.assertEqual((out/'strategy-artifacts/workflows/chosen.py').read_text(),'[REDACTED]')


if __name__ == '__main__':
    unittest.main()
