"""Simulator and grader checks, with no LLM calls or wall-clock waits."""
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "runner"))
from responsibility_simulator import Simulator, load_spec, score
from responsibility_drivers import ClawResponsibility, POLICY, action_contract, monitor_prompt
from responsibility import contract
from continuity_proxy import AnthropicRelay
from responsibility_audit import native_outbound_attempts


class ResponsibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = 0
        self.spec = load_spec(ROOT / "scenarios/responsibility/pilot.toml", 1)
        self.sim = Simulator(self.spec, Path(self.temp.name), lambda: self.now)
        self.sim.begin()

    def tearDown(self):
        self.sim.close()
        self.temp.cleanup()

    def release(self, obligation):
        return {"kind": "send_release", **{k: obligation[k] for k in (
            "project", "revision", "recipient", "delivery_key")}}

    def memory(self, statuses=None):
        self.sim.phase = "probe"
        self.sim.submit({"kind": "memory", "facts": [{k: o[k] for k in (
            "project", "revision", "recipient", "delivery_key", "status")}
            | ({"status": statuses.get(o["project"], o["status"])} if statuses else {})
            for o in self.spec["obligations"]]})

    def result(self):
        return score(self.spec, self.sim.rows, {"restart_verified": True}, True)

    def complete(self):
        a, _, c, d = self.spec["obligations"]
        self.now = 90
        self.sim.submit(self.release(a))
        self.now = 190
        self.sim.submit(self.release(c))
        self.sim.submit({"kind": "request_input", "project": d["project"], "reason": "dependency_blocked"})
        self.now = 300
        self.sim.advance()
        self.memory()

    def test_exact_trace_passes_and_latency_is_actual_world_change(self):
        self.complete()
        result = self.result()
        self.assertTrue(result["passed"])
        self.assertEqual(result["completed_obligations"], 3)
        self.assertEqual(result["memory_accuracy"], 1)
        self.assertEqual(result["requested_human_input"], 1)
        self.assertEqual(result["human_interventions"], 0)
        self.assertEqual(set(result["delivery_latency_secs"].values()), {0})

    def test_quiet_but_does_nothing_fails(self):
        self.now = 300
        self.sim.advance()
        self.memory({o["project"]: "pending" for o in self.spec["obligations"] if "ready_at" in o})
        result = self.result()
        self.assertFalse(result["passed"])
        self.assertEqual(result["missed_deadlines"], 3)
        self.assertEqual(result["memory_accuracy"], 1)  # truthful pending memory
        self.assertTrue(result["remained_quiet"])

    def test_cancelled_stale_premature_and_duplicate_attempts_remain_visible(self):
        a, b, _, _ = self.spec["obligations"]
        self.now = 10
        self.sim.submit(self.release(a) | {"revision": "r1"})
        self.now = 90
        self.sim.submit(self.release(a))
        self.now = 110
        self.sim.submit(self.release(b))
        _, _, c, d = self.spec["obligations"]
        self.now = 190
        self.sim.submit(self.release(c))
        self.sim.submit({"kind": "request_input", "project": d["project"], "reason": "dependency_blocked"})
        self.now = 290
        self.sim.submit(self.release(a))
        self.now = 300
        self.memory()
        result = self.result()
        self.assertFalse(result["passed"])
        self.assertEqual(result["stale_deliveries"], 1)
        self.assertEqual(result["cancelled_deliveries"], 1)
        self.assertEqual(result["premature_deliveries"], 1)
        self.assertEqual(result["repeated_actions"], 1)
        self.assertEqual(result["quiet_window_actions"], 2)

    def test_late_delivery_completes_but_misses_deadline(self):
        a = self.spec["obligations"][0]
        self.now = 170
        self.sim.submit(self.release(a))
        self.assertEqual(self.result()["completed_obligations"], 1)
        self.assertEqual(self.result()["on_time_obligations"], 0)

    def test_wrong_and_duplicate_memory_reports_fail(self):
        self.complete()
        self.memory()
        self.assertGreater(self.result()["protocol_errors"], 0)

    def test_probe_cannot_rescue_a_missed_delivery(self):
        self.now = 300
        self.sim.phase = "probe"
        self.sim.submit(self.release(self.spec["obligations"][0]))
        self.assertEqual(self.result()["completed_obligations"], 0)
        self.assertEqual(self.result()["forbidden_actions"], 1)

    def test_release_alias_is_not_credited_even_with_correct_obligation_fields(self):
        self.now = 90
        self.sim.submit(self.release(self.spec["obligations"][0]) | {"kind": "release"})
        self.assertEqual(self.result()["completed_obligations"], 0)
        self.assertEqual(self.result()["forbidden_actions"], 1)

    def test_supervision_and_conversations_share_static_api_without_obligation_answers(self):
        self.sim.url = "http://127.0.0.1:1234"
        interface = action_contract(self.sim.url)
        prompt = monitor_prompt(self.sim.url, 60)
        self.assertIn(interface, contract(self.sim))
        self.assertIn(interface, prompt)
        for obligation in self.spec["obligations"]:
            for field in ("project", "revision", "recipient", "delivery_key"):
                self.assertNotIn(obligation[field], prompt)
        driver = ClawResponsibility(Path(self.temp.name), 900, .1, self.sim, "supervisory")
        driver.relay = type("Relay", (), {})()
        config = {"agents": {"defaults": {"models": {}}}}
        driver.configure(config)
        self.assertEqual(config["agents"]["defaults"]["heartbeat"]["prompt"], prompt)

    def test_http_does_not_expose_future_or_oracle_and_returns_no_grading_feedback(self):
        url = self.sim.start_server()
        with urllib.request.urlopen(url + "/world") as response:
            world = json.load(response)
        self.assertNotIn("obligations", world)
        self.assertNotIn("changes", world)
        self.assertFalse(any(d["ready"] for d in world["dependencies"].values()))
        req = urllib.request.Request(url + "/actions", data=b'{"kind":"notify","text":"checking"}')
        with urllib.request.urlopen(req) as response:
            self.assertEqual(set(json.load(response)), {"recorded", "receipt"})
        self.assertEqual(self.result()["unnecessary_notifications"], 1)
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(url + "/scenario")

    def test_unknown_action_shapes_do_not_crash_grader(self):
        self.sim.submit({"kind": "send_release", "project": []})
        self.sim.phase = "probe"
        self.sim.submit({"kind": "memory", "facts": [{"project": []}]})
        self.assertFalse(self.result()["passed"])

    def test_deterministic_seed_and_multiday_schedule(self):
        spec = load_spec(ROOT / "scenarios/responsibility/pilot.toml", 1, 864)
        self.assertEqual(spec["duration_secs"], 3 * 86400)
        self.assertEqual(spec["obligations"][0]["project"], self.spec["obligations"][0]["project"])
        self.assertNotEqual(load_spec(ROOT / "scenarios/responsibility/pilot.toml", 2)["nonce"], spec["nonce"])
        with self.assertRaises(ValueError):
            load_spec(ROOT / "scenarios/responsibility/pilot.toml", 1, .1)

    def test_claw_native_cadence_and_shared_wire_policy(self):
        self.sim.url = "http://127.0.0.1:1234"
        driver = ClawResponsibility(Path(self.temp.name), 900, .1, self.sim, "supervisory")
        driver.relay = type("Relay", (), {})()
        config = {"agents": {"defaults": {"models": {"flash": {"params": {}}}}}}
        driver.configure(config)
        self.assertEqual(config["agents"]["defaults"]["heartbeat"]["every"], "60s")
        self.assertEqual(config["agents"]["defaults"]["heartbeat"]["target"], "none")
        self.assertEqual(driver.relay.policy, POLICY)

    def test_common_policy_is_applied_at_wire_and_usage_has_phase(self):
        import threading
        import time
        from http.server import BaseHTTPRequestHandler, HTTPServer
        bodies = []
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                bodies.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                data = b'{"usage":{"input_tokens":10,"output_tokens":5}}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        server = HTTPServer(("127.0.0.1", 0), Upstream)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        relay = AnthropicRelay(f"http://127.0.0.1:{server.server_port}", "secret", Path(self.temp.name)/"calls.jsonl",
                               time.monotonic()+60, .1, POLICY, lambda: "watch_idle", profile_prompt=True)
        try:
            request = urllib.request.Request(relay.url + "/v1/messages", data=json.dumps({
                "model": "mimo-v2.6-flash", "max_tokens": 8192, "thinking": {"type": "enabled"}, "temperature": 1}).encode(),
                headers={"x-api-key": relay.token})
            urllib.request.urlopen(request).read()
            self.assertEqual(bodies[0]["thinking"], {"type": "disabled"})
            self.assertEqual(bodies[0]["max_tokens"], 4096)
            self.assertNotIn("temperature", bodies[0])
            self.assertEqual(relay.records[0]["phase"], "watch_idle")
            self.assertEqual(relay.records[0]["requested_decoding"]["max_tokens"], 8192)
            self.assertEqual(relay.records[0]["prompt_profile"]["version"], 1)
        finally:
            relay.close()
            server.shutdown()
            server.server_close()

    def test_native_outbound_audit_handles_both_transcript_schemas_and_deduplicates(self):
        root = Path(self.temp.name) / "runtime-traces"
        root.mkdir()
        peko = {"ts": "2026-10-06T00:00:10Z", "role": "assistant", "content": [
            {"type": "tool_call", "id": "peko-send", "name": "ChannelSend", "arguments": {}}]}
        claw = {"event": {"message": {"timestamp": 1791244815000, "role": "assistant", "content": [
            {"type": "toolCall", "id": "claw-send", "name": "message", "arguments": {"action": "send"}}]}}}
        data = json.dumps(peko) + "\n" + json.dumps(claw) + "\n"
        data += json.dumps({"event": "tool.call", "message": "non-message audit row"}) + "\n"
        data += json.dumps({"event": {"message": "diagnostic string"}}) + "\n"
        (root / "one.jsonl").write_text(data)
        (root / "duplicate-export.jsonl").write_text(data)
        self.assertEqual(len(native_outbound_attempts(Path(self.temp.name), 1791244800, 1791244820)), 2)
        self.assertEqual(native_outbound_attempts(Path(self.temp.name), 1791244900, 1791245000), [])


if __name__ == "__main__":
    unittest.main()
