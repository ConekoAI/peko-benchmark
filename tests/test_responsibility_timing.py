import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'runner'))
from responsibility_timing import native_cron_timing
from responsibility_drivers import task_monitor_prompt
from responsibility import settled_telemetry


class NativeTimingTests(unittest.TestCase):
    def fixture(self, root, details):
        audit = root / 'runtime-traces/data/runtime/audit'
        audit.mkdir(parents=True)
        snapshot = {'schedule': {'jobs': [{'id': 'worker', 'schedule': {'every_ms': 60000}}],
                                'runs': [{'id': 'open', 'job_id': 'worker', 'started_at': 180,
                                          'finished_at': None, 'status': 'running'}]}}
        (root / 'topology-post-watch.json').write_text(json.dumps(snapshot))
        event = {'event_type': 'cron.result', 'details': details}
        # Mirrored/double-read audit evidence must not double-count the turn.
        (audit / 'audit.jsonl').write_text(json.dumps(event) + '\n' + json.dumps(event) + '\n')

    def test_overrun_skip_and_open_run_remain_distinct(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root, {'run_id': 'done', 'job_id': 'worker', 'job_name': 'responsibility-monitor',
                                'status': 'success', 'scheduled_at': 100, 'finished_at': 162,
                                'next_run_at': 220, 'duration_ms': 60759, 'skipped_interval_slots': 1})
            result = native_cron_timing(root, 90, 200)
            self.assertTrue(result['measured'])
            self.assertEqual(result['worker_completed_runs'], 1)
            self.assertEqual(result['worker_turns_exceeding_interval'], 1)
            self.assertEqual(result['worker_skipped_interval_slots'], 1)
            self.assertEqual(result['worker_max_turn_secs'], 60.759)
            self.assertEqual(result['runs'][0]['late_admission_secs'], 1.241)
            self.assertEqual(result['open_runs_at_snapshot'], ['open'])
            self.assertFalse(native_cron_timing(root, 300, 400)['measured'])

    def test_legacy_fields_are_unmeasured_not_zero_skipped_slots(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root, {'run_id': 'done', 'job_id': 'worker', 'status': 'success', 'duration_ms': 60759})
            self.assertFalse(native_cron_timing(root, 90, 200)['measured'])

    def test_lean_worker_keeps_durable_writes_and_no_extra_polling(self):
        prompt = task_monitor_prompt('http://127.0.0.1:1234', 60, True)
        for fragment in ('one model response', 'runtime may serialize', 'Keep exact payloads and receipts',
                         'at most one short sentence', 'Do not wait, add polling, drop durable writes',
                         'Make at most one GET', 'not_before'):
            self.assertIn(fragment, prompt)

    def test_interrupted_usage_is_explained_without_forgiving_native_gate(self):
        from types import SimpleNamespace
        from continuity_proxy import summarize_calls
        calls = [{'index': 1, 'forwarded': True, 'status': 200, 'completed': True,
                  'usage': {'input_tokens': 10, 'output_tokens': 5}},
                 {'index': 2, 'forwarded': True, 'status': 200, 'completed': True,
                  'downstream_disconnected': True,
                  'usage': {'input_tokens': 3, 'output_tokens': 2, 'cache_read_input_tokens': 100}}]
        native = summarize_calls(calls[:1])
        relay = SimpleNamespace(records=calls, telemetry=lambda: summarize_calls(calls))
        result = settled_telemetry(relay, {'native_usage': native})
        self.assertFalse(result['native_usage_matches'])
        self.assertTrue(result['native_reconciliation_diagnostic']['difference_exactly_explained_by_disconnected_calls'])
        self.assertEqual(result['native_reconciliation_diagnostic']['disconnected_request_indices'], [2])
        calls[-1]['completed'] = False
        incomplete = settled_telemetry(relay, {'native_usage': native})
        self.assertFalse(incomplete['native_reconciliation_diagnostic']['difference_exactly_explained_by_disconnected_calls'])
