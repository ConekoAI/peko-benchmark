import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runner"))
from prompt_profile import PromptProfiler
from profile_usage import analyze


class PromptProfileTests(unittest.TestCase):
    def payload(self):
        return {"model": "mimo-v2.6-flash", "max_tokens": 4096,
                "tools": [{"name": "private-tool", "description": "private notes"}],
                "system": [{"type": "text", "text": "private instructions"}],
                "messages": [{"role": "user", "content": "private input"}]}

    def test_no_plaintext_or_payload_mutation_and_run_local_keys(self):
        payload = self.payload()
        saved = copy.deepcopy(payload)
        profile = PromptProfiler().capture(payload, 1)
        self.assertEqual(payload, saved)
        self.assertNotIn("private", json.dumps(profile))
        other = PromptProfiler().capture(payload, 1)
        self.assertNotEqual(profile["system_hash"], other["system_hash"])
        self.assertEqual(profile["tool_count"], 1)

    def test_append_only_prefix_and_interleaved_sessions(self):
        profiler = PromptProfiler(b"test")
        payload = self.payload()
        profiler.capture(payload, 1)
        other = copy.deepcopy(payload)
        other["messages"][0]["content"] = "another conversation"
        profiler.capture(other, 2)
        payload["messages"].append({"role": "assistant", "content": "reply"})
        result = profiler.capture(payload, 3)
        self.assertEqual(result["best_previous_request"], 1)
        self.assertEqual(result["shared_message_prefix_count"], 1)
        self.assertTrue(result["extends_previous_request"])

    def test_prefix_edits_and_parameter_changes_are_detected(self):
        profiler = PromptProfiler(b"test")
        payload = self.payload()
        profiler.capture(payload, 1)
        payload["messages"][0]["content"] += " changed"
        result = profiler.capture(payload, 2)
        self.assertEqual(result["shared_message_prefix_count"], 0)
        self.assertFalse(result["extends_previous_request"])
        payload["max_tokens"] = 8192
        self.assertIsNone(profiler.capture(payload, 3)["best_previous_request"])

    def test_cache_marker_movement_does_not_change_content_fingerprints(self):
        profiler = PromptProfiler(b"test")
        payload = self.payload()
        payload["messages"][0]["content"] = [{"type": "text", "text": "private input"}]
        first = profiler.capture(payload, 1)
        payload["tools"][0]["cache_control"] = {"type": "ephemeral"}
        payload["messages"][0]["content"][0]["cache_control"] = {"type": "ephemeral"}
        result = profiler.capture(payload, 2)
        self.assertEqual(result["tools_hash"], first["tools_hash"])
        self.assertTrue(result["extends_previous_request"])
        self.assertEqual(result["cache_marker_locations"], [
            {"field": "tools", "item": 0}, {"field": "messages", "item": 0, "block": 0}])

    def test_unexpected_role_cannot_leak_plaintext(self):
        payload = self.payload()
        payload["messages"][0]["role"] = "private role"
        profile = PromptProfiler().capture(payload, 1)
        self.assertEqual(profile["messages"][0]["role"], "other")
        self.assertNotIn("private", json.dumps(profile))

    def test_offline_phase_accounting_and_native_duplicate_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = PromptProfiler(b"test").capture(self.payload(), 1)
            rows = [{"index": 1, "forwarded": True, "completed": True, "status": 200,
                     "phase": "watch_active", "usage": {"input_tokens": 10, "output_tokens": 2,
                     "cache_read_input_tokens": 90}, "prompt_profile": profile},
                    {"index": 2, "forwarded": True, "completed": False, "status": 200,
                     "phase": "watch_idle", "usage": {"input_tokens": 20}}]
            (root / "provider-calls.jsonl").write_text("\n".join(map(json.dumps, rows)))
            traces = root / "runtime-traces"
            traces.mkdir()
            text = "<runtime-context>\n## Session context\nWatch\n## session_context\nWatch\n</runtime-context>"
            message = {"type": "message.v2", "role": "user", "message_id": "one",
                       "role_metadata": {"User": {"source": "hook"}},
                       "content": [{"type": "text", "text": text}]}
            (traces / "one.jsonl").write_text(json.dumps(message) + "\n" + json.dumps(message))
            result = analyze(root)
            self.assertEqual(result["phases"]["watch_active"]["cache_read_fraction"], .9)
            self.assertEqual(result["phases"]["watch_active"]["profiled_calls"], 1)
            self.assertIsNone(result["phases"]["watch_idle"]["cost_usd"])
            self.assertEqual(result["phases"]["watch_idle"]["zero_cache_read_calls"], 0)
            self.assertEqual(result["phases"]["watch_idle"]["incomplete_cache_usage_calls"], 1)
            self.assertEqual(result["peko_runtime_context"]["duplicate_session_context_messages"], 1)
            self.assertEqual(result["peko_runtime_context"]["total_characters"], len(text))
