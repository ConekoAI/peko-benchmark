"""Simulator and grader checks, with no LLM calls or wall-clock waits."""
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "runner"))
from responsibility_simulator import Simulator, load_spec, score, cadence_coverage
from responsibility_drivers import (ClawResponsibility, POLICY, action_contract, state_contract,
                                    monitor_prompt, task_monitor_prompt)
from responsibility import contract
from continuity_proxy import AnthropicRelay
from responsibility_audit import native_outbound_attempts
from responsibility_topology import (verify_peko, verify_claw, execution_evidence,
                                     supervisor_prompt, WORKER_KEY, SEPARATED_CONTRACT_VERSION)
from responsibility_topology import direct_action_prompt


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
        self.assertIn(state_contract(), contract(self.sim))
        self.assertIn(state_contract(), prompt)
        for obligation in self.spec["obligations"]:
            for field in ("project", "revision", "recipient", "delivery_key"):
                self.assertNotIn(obligation[field], prompt)
        driver = ClawResponsibility(Path(self.temp.name), 900, .1, self.sim, "supervisory")
        driver.relay = type("Relay", (), {})()
        config = {"agents": {"defaults": {"models": {}}}}
        driver.configure(config)
        self.assertEqual(config["agents"]["defaults"]["heartbeat"]["prompt"], prompt)

    def test_coverage_distinguishes_no_inspection_from_inspection_without_delivery(self):
        self.now = 90
        self.sim.observe()
        self.now = 174
        self.sim.observe()
        self.now = 242
        self.sim.observe()
        self.now = 300
        self.sim.record("watch_finished")
        result = self.result()
        coverage = result["cadence_coverage"]
        a, _, c, d = self.spec["obligations"]
        self.assertEqual(result["completed_obligations"], 0)
        self.assertEqual(coverage["obligations_observed_in_time"], 2)
        self.assertEqual(coverage["obligations_without_timely_observation"], [d["project"]])
        self.assertEqual(coverage["obligations"][a["project"]]["eligible_read_times_secs"], [90])
        self.assertEqual(coverage["obligations"][c["project"]]["max_remaining_secs"], 66)
        self.assertEqual(coverage["max_inter_read_gap_secs"], 84)
        self.assertEqual(coverage["max_unobserved_gap_secs"], 90)
        self.assertEqual(coverage["first_read_offset_mod_cadence_secs"], 30)

    def test_coverage_uses_actual_ready_revision_not_planned_time_or_future_changes(self):
        a, _, c, d = self.spec["obligations"]
        a["deadline"] = 220  # Isolate revision matching from the normal 160s cutoff.
        self.now = 90
        self.sim.observe()
        self.sim.rows[-2]["change"]["revision"] = "r1"
        self.now = 174
        self.sim.observe()
        self.now = 190
        self.sim.observe()
        coverage = cadence_coverage(self.spec, self.sim.rows)
        self.assertEqual(coverage["obligations"][a["project"]]["eligible_read_times_secs"], [190])
        self.assertEqual(coverage["obligations"][c["project"]]["eligible_read_times_secs"], [174, 190])
        self.assertEqual(coverage["obligations"][d["project"]]["eligible_read_times_secs"], [190])
        self.assertFalse(coverage["watch_complete"])
        self.assertEqual(coverage["observation_horizon_secs"], 190)

    def test_coverage_empty_watch_and_deadline_boundaries_do_not_change_grade(self):
        self.now = 300
        self.sim.record("watch_finished")
        coverage = self.result()["cadence_coverage"]
        self.assertEqual(coverage["max_unobserved_gap_secs"], 300)
        self.assertIsNone(coverage["first_read_elapsed_secs"])
        self.assertEqual(coverage["obligations_observed_in_time"], 0)
        a = self.spec["obligations"][0]
        rows = [{"kind": "world_change", "phase": "watch", "elapsed_secs": 159,
                 "change": {"project": a["project"], "ready": True, "revision": a["revision"]}},
                {"kind": "read", "phase": "watch", "elapsed_secs": 160},
                {"kind": "read", "phase": "probe", "elapsed_secs": 160},
                {"kind": "read", "phase": "watch", "elapsed_secs": 160.001}]
        details = cadence_coverage(self.spec, rows)["obligations"][a["project"]]
        self.assertEqual(details["eligible_read_count"], 1)
        self.assertEqual(details["min_remaining_secs"], 0)

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

    def test_separated_contract_allows_direct_workers_but_keeps_original_task(self):
        self.sim.url = "http://127.0.0.1:1234"
        original = contract(self.sim)
        self.spec["topology"] = "separated"
        separated = contract(self.sim)
        self.assertIn("or delegated monitors", original)
        self.assertNotIn("or delegated monitors", separated)
        self.assertIn("Only the task worker", separated)
        self.assertIn(action_contract(self.sim.url), separated)
        self.assertIn(state_contract(), separated)
        worker = task_monitor_prompt(self.sim.url, self.spec['cadence_secs'])
        self.assertIn(direct_action_prompt(self.sim.url), separated)
        self.assertIn(direct_action_prompt(self.sim.url), worker)
        for obligation in self.spec["obligations"]:
            for field in ("project", "revision", "recipient", "delivery_key"):
                self.assertNotIn(obligation[field], worker)
        self.assertIn("120s", separated)
        driver = ClawResponsibility(Path(self.temp.name), 900, .1, self.sim, "supervisory")
        driver.relay = type("Relay", (), {})()
        config = {"agents": {"defaults": {"models": {}}}}
        driver.configure(config)
        hb = config["agents"]["defaults"]["heartbeat"]
        self.assertEqual(hb["every"], "120s")
        self.assertEqual(hb["prompt"], supervisor_prompt(60))

    def test_peko_topology_rejects_another_label_that_still_runs_in_trunk(self):
        sessions = {"root": {"session_id": "root", "parent_session_id": None},
                    "worker": {"session_id": "worker", "parent_session_id": "root", "slug": "release-watch"}}
        task = {"id": "task", "name": "responsibility-monitor", "enabled": True,
                "kind": "spawn_tool", "tool_name": "Agent", "wake_on_completion": False,
                "tool_params": {"action": "new", "path": "/release-watch", "role": "release-watch", "prompt": "work"},
                "schedule": {"every_ms": 60000}}
        keep = {"id": "org", "name": "organization-supervisor", "enabled": True,
                "kind": "send", "schedule": {"every_ms": 120000}}
        self.assertTrue(verify_peko({"jobs": [task, keep]}, sessions, 60)["verified"])
        task["kind"] = "send"
        self.assertFalse(verify_peko({"jobs": [task, keep]}, sessions, 60)["verified"])
        task["kind"] = "spawn_tool"
        task["tool_params"]["path"] = "/"
        self.assertFalse(verify_peko({"jobs": [task, keep]}, sessions, 60)["verified"])
        task["tool_params"]["path"] = "/release-watch"
        self.assertFalse(verify_peko({"jobs": [task, keep, keep]}, sessions, 60)["verified"])

    def test_failed_onboarding_retains_contract_and_bootstrap_evidence(self):
        self.sim.url = "http://127.0.0.1:1234"
        self.spec["topology"] = "separated"
        driver = ClawResponsibility(Path(self.temp.name), 900, .1, self.sim, "supervisory")
        driver.workspace = Path(self.temp.name)
        driver.node, driver.entry = "node", Path("openclaw.mjs")
        (driver.workspace / "BOOTSTRAP.md").write_text("Not completed")
        def baseline(_):
            driver.metadata = {"initialization_completed": True}
            return driver.metadata
        with patch("responsibility_drivers.OpenClawDriver.start", baseline), \
                patch.object(driver, "turn", side_effect=TimeoutError("onboarding")):
            with self.assertRaises(TimeoutError):
                driver.start()
        self.assertEqual(driver.metadata["api_contract_version"], SEPARATED_CONTRACT_VERSION)
        self.assertEqual(driver.metadata["topology"], "separated")
        self.assertFalse(driver.metadata["persona_bootstrap_completed"])

    def test_claw_topology_requires_custom_agent_session_not_a_supervisor_event(self):
        task = {"name": "responsibility-monitor", "enabled": True,
                "payload": {"kind": "agentTurn"}, "sessionTarget": "session:release-watch",
                "schedule": {"everyMs": 60000}, "delivery": {"mode": "none"}}
        keep = {"enabled": True, "payload": {"kind": "heartbeat"}, "schedule": {"everyMs": 120000}}
        builtin = {"enabled": True, "declarationKey": "memory-core:memory-dreaming-promotion"}
        sessions = {"sessions": [{"key": WORKER_KEY, "sessionId": "worker"}]}
        self.assertTrue(verify_claw({"jobs": [task, keep, builtin]}, sessions, 60)["verified"])
        task["sessionTarget"] = "main"
        self.assertFalse(verify_claw({"jobs": [task, keep]}, sessions, 60)["verified"])

    def test_execution_evidence_requires_both_lanes_and_rejects_trunk_operations(self):
        root = Path(self.temp.name) / "runtime-traces"
        root.mkdir()
        def row(role, cmd=None):
            return {"type": "message.v2", "id": role, "ts": "2026-10-06T00:00:10Z",
                    "role": "assistant", "content": [{"type": "tool_call", "id": role,
                    "name": "Bash", "arguments": {"command": cmd}}] if cmd else []}
        (root / "worker.jsonl").write_text(json.dumps(row("w", "curl http://localhost/world"))+'\n')
        (root / "supervisor.jsonl").write_text(json.dumps(row("s"))+'\n')
        ids = {"worker_session_ids": ["worker"], "supervisor_session_ids": ["supervisor"]}
        result = execution_evidence(Path(self.temp.name), 1791244800, 1791244820, ids)
        self.assertTrue(result["verified"])
        self.assertEqual(result["worker_world_tool_calls"], 1)
        (root / "supervisor.jsonl").write_text(json.dumps(row("s", "curl http://localhost/actions"))+'\n')
        result = execution_evidence(Path(self.temp.name), 1791244800, 1791244820, ids)
        self.assertFalse(result["verified"])
        self.assertEqual(result["nonworker_operational_tool_calls"], 1)

    def test_journal_prose_and_wrong_tool_are_not_operational_http_intents(self):
        from responsibility_topology import direct_http_endpoints
        self.assertEqual(direct_http_endpoints("cat >> journal.md <<'EOF'\nNo /world GET or /actions POST.\nEOF"),set())
        self.assertEqual(direct_http_endpoints("curl -sS --data '{\"note\":\"/world\"}' http://localhost/actions"),{'/actions'})

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
