import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'runner'))
from responsibility_diagnostics import observed_preconditions, retained_receipts
from responsibility_simulator import Simulator, load_spec, score
from continuity_proxy import AnthropicRelay, summarize_calls
from responsibility_prepared import empty_notes

ROOT = Path(__file__).resolve().parent.parent


class DiagnosticsTests(unittest.TestCase):
    def test_post_clock_readiness_does_not_prove_observed_readiness(self):
        with tempfile.TemporaryDirectory() as folder:
            now = [0]; spec = load_spec(ROOT / 'scenarios/responsibility/pilot.toml', 1)
            sim = Simulator(spec, Path(folder), lambda: now[0]); sim.begin()
            now[0] = 65; sim.observe(); now[0] = 75
            payload = {'kind': 'send_release', **{k: spec['obligations'][0][k] for k in ('project', 'revision', 'recipient', 'delivery_key')}}
            sim.submit(payload)
            self.assertEqual(score(spec, sim.rows, {}, True)['completed_obligations'], 1)
            diag = observed_preconditions(spec, sim.rows)
            self.assertEqual(diag['violations'], 1)
            now[0] = 80; sim.observe(); sim.submit(payload)
            self.assertTrue(observed_preconditions(spec, sim.rows)['actions'][-1]['observed_precondition_satisfied'])
            legacy = [dict(r) for r in sim.rows]
            for row in legacy: row.pop('snapshot', None)
            self.assertEqual(observed_preconditions(spec, legacy)['violations'], 1)

    def test_receipt_loss_and_unrelated_numbers_are_distinguished(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); log = root / 'runtime-traces/workspace/kb/responsibility/receipts.md'
            log.parent.mkdir(parents=True); log.write_text('| elapsed | receipt |\n|---|---|\n| 9 | 13 |\n')
            rows = [{'seq': i, 'kind': 'action', 'action': {'kind': 'send_release'}} for i in (9, 13, 19)]
            self.assertEqual(retained_receipts(root, rows)['missing_receipts'], [9, 19])

    def test_prepared_notes_contain_no_obligation_facts(self):
        with tempfile.TemporaryDirectory() as folder:
            empty_notes(Path(folder), 'static worker instruction')
            self.assertNotIn('atlas', ''.join(p.read_text() for p in Path(folder).rglob('*.md')))
            self.assertIn('No commitments', (Path(folder) / 'kb/responsibility/commitments.md').read_text())

    def test_missing_probe_is_unmeasured_not_a_memory_inference(self):
        spec = load_spec(ROOT / 'scenarios/responsibility/pilot.toml', 1)
        self.assertEqual(score(spec, [], {}, False)['memory_measurement'], 'unmeasured')

    def test_probe_allowance_preserves_operating_rejections_and_full_usage(self):
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                body = b'{"usage":{"input_tokens":10,"output_tokens":5}}'
                self.send_response(200); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        with tempfile.TemporaryDirectory() as folder:
            server = HTTPServer(('127.0.0.1', 0), Upstream)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            phase = ['watch_active']; policy = {'max_tokens': 4096, 'thinking': {'type': 'disabled'}, 'request_limit': 1,
                'probe_allowance': {'request_limit': 1, 'output_limit': 100, 'budget_usd': .01}}
            relay = AnthropicRelay(f'http://127.0.0.1:{server.server_port}', 'secret', Path(folder)/'calls.jsonl', time.monotonic()+60, .1, policy, lambda: phase[0])
            def call():
                req = urllib.request.Request(relay.url+'/v1/messages', data=b'{"model":"mimo-v2.6-flash","max_tokens":4096}', headers={'x-api-key': relay.token})
                return urllib.request.urlopen(req).read()
            try:
                call()
                with self.assertRaises(urllib.error.HTTPError) as rejected: call()
                self.assertEqual(rejected.exception.code, 429)
                phase[0] = 'probe'; call()
                with self.assertRaises(urllib.error.HTTPError): call()
                phase[0] = 'watch_idle'
                with self.assertRaises(urllib.error.HTTPError): call()
                usage = summarize_calls(relay.records)
                self.assertEqual(usage['request_count'], 2); self.assertEqual(usage['rejected_request_count'], 3)
                self.assertEqual(usage['uncached_input_tokens'], 20); self.assertTrue(usage['usage_complete'])
            finally:
                relay.close(); server.shutdown(); server.server_close()

    def test_prepared_peko_uses_fresh_empty_child_and_native_job_payloads(self):
        from types import SimpleNamespace
        from responsibility_prepared import prepare_peko, arm_peko
        from responsibility_topology import verify_peko
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder); root = home / '.peko/data/principals/bench'
            index = root / 'sessions/sessions.json'; index.parent.mkdir(parents=True)
            index.write_text(json.dumps({'root': {'session_id': 'root', 'parent_session_id': None,
                'total_input_tokens': 42, 'message_count': 5, 'agent_name': 'root'}}))
            path = root / 'cron/schedule.toml'; path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'version': 2, 'jobs': [], 'runs': []}))
            workspace=home/'.peko/principals/bench';workspace.mkdir(parents=True)
            (workspace/'principal.toml').write_text('id = "principal-test"\n')
            driver = SimpleNamespace(temp=SimpleNamespace(name=folder), principal='bench', sim=SimpleNamespace(spec={'cadence_secs': 60}),
                metadata={}, _stop_owned_daemon=lambda: None, _command=lambda *args: None, _ready=lambda: None)
            prepare_peko(driver, 'static worker instruction')
            schedule = json.loads(path.read_text()); sessions = json.loads(index.read_text())
            check = verify_peko(schedule, sessions, 60)
            self.assertTrue(check['verified'], check)
            child = sessions[check['worker_session_ids'][0]]
            self.assertEqual(child['message_count'], 0); self.assertEqual(child['total_input_tokens'], 0)
            self.assertEqual(index.with_name(child['transcript_file']).read_text(), '')
            self.assertEqual(schedule['runs'], [])
            arm_peko(driver)
            self.assertTrue(verify_peko(json.loads(path.read_text()), sessions, 60)['verified'])

    def test_claw_clock_preparation_respects_system_owned_heartbeat(self):
        from types import SimpleNamespace
        from responsibility_prepared import set_claw_due_times
        calls = []
        jobs = {'jobs': [{'id': 'worker', 'name': 'responsibility-monitor', 'payload': {'kind': 'agentTurn'}},
                         {'id': 'supervisor', 'payload': {'kind': 'heartbeat'}}]}
        def command(*args):
            if args[0] == 'automations': return json.dumps(jobs)
            calls.append(args); return '{}'
        driver = SimpleNamespace(sim=SimpleNamespace(spec={'cadence_secs': 60}), _command=command,
                                 _stop_gateway=lambda: None, _start_gateway=lambda: None)
        with patch('responsibility_prepared.time.time', return_value=1000): set_claw_due_times(driver, True)
        self.assertEqual(calls[0], ('config','set','agents.defaults.heartbeat.every','120s'))
        params = json.loads(calls[1][calls[1].index('--params')+1])
        self.assertEqual(params['id'], 'worker')
        self.assertEqual(params['patch']['schedule'], {'kind':'every','everyMs':60000,'anchorMs':1020000})
        calls.clear()
        with patch('responsibility_prepared.time.time', return_value=1000): set_claw_due_times(driver, False)
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(calls[0][calls[0].index('--params')+1])['patch']['schedule']['anchorMs'], 4600000)

    def test_policy_recall_requires_explicit_deadlines_thresholds_and_nulls(self):
        spec = load_spec(ROOT / 'scenarios/responsibility/pilot.toml', 1)
        spec['measure_memory_policy'] = True
        facts = [{k:o.get(k) for k in ('project','revision','recipient','delivery_key','deadline','blocked_at')}
                 | {'status': 'cancelled' if o.get('cancelled') else 'blocked' if 'blocked_at' in o else 'pending'}
                 for o in spec['obligations']]
        rows = [{'kind':'action','seq':1,'phase':'probe','elapsed_secs':300,'action':{'kind':'memory','facts':facts}}]
        result = score(spec, rows, {}, True)
        self.assertEqual(result['memory_facts_total'], 24); self.assertEqual(result['memory_facts_correct'], 24)
        facts[-1]['blocked_at'] = 0
        self.assertEqual(score(spec, rows, {}, True)['memory_facts_correct'], 23)
        del facts[0]['blocked_at']
        self.assertEqual(score(spec, rows, {}, True)['memory_facts_correct'], 22)

    def test_memory_probe_example_contains_every_scored_policy_key(self):
        from types import SimpleNamespace
        from responsibility import memory_probe_prompt
        spec = load_spec(ROOT / 'scenarios/responsibility/pilot.toml', 1)
        spec['measure_memory_policy'] = True
        prompt = memory_probe_prompt(SimpleNamespace(spec=spec, url='http://example.invalid'))
        self.assertIn('"deadline": null', prompt); self.assertIn('"blocked_at": null', prompt)
        self.assertIn('Do not omit these keys', prompt)

    def test_probe_suspension_preserves_peko_jobs_history_and_due_times(self):
        from types import SimpleNamespace
        from responsibility_prepared import pause_peko_for_probe, pause_claw_for_probe
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'.peko/data/principals/bench/cron/schedule.toml'; path.parent.mkdir(parents=True)
            schedule = {'jobs':[{'id':'worker','enabled':True,'next_run':'future'}],'runs':[{'status':'success'}]}
            path.write_text(json.dumps(schedule)); calls=[]
            driver=SimpleNamespace(temp=SimpleNamespace(name=folder),principal='bench',metadata={},
                _stop_owned_daemon=lambda: None,_ready=lambda: None,_command=lambda *a: calls.append(a))
            pause_peko_for_probe(driver)
            updated=json.loads(path.read_text());self.assertFalse(updated['jobs'][0]['enabled'])
            self.assertEqual(updated['jobs'][0]['next_run'],'future');self.assertEqual(updated['runs'],schedule['runs'])
            self.assertTrue(driver.metadata['probe_schedules_suspended'])
        calls=[]
        def command(*args):
            calls.append(args)
            return json.dumps({'jobs':[{'id':'w','name':'responsibility-monitor'},{'id':'h','payload':{'kind':'heartbeat'}}]}) if args[:2]==('automations','list') else '{}'
        driver=SimpleNamespace(metadata={},_command=command,_stop_gateway=lambda:None,_start_gateway=lambda:None)
        pause_claw_for_probe(driver)
        self.assertIn(('config','set','agents.defaults.heartbeat.every','0m'),calls)
        self.assertIn(('automations','edit','w','--disable'),calls)
        self.assertFalse(any(a[:2]==('automations','edit') and a[2]=='h' for a in calls))
