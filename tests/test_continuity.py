"""Grader mutation checks and adapter contracts, without credentials or model calls."""
import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "runner"))
from continuity import execute, load_scenario, parse_actions, score_scenario, ValidationDriver
from continuity_peko import PekoDriver
from continuity_usage import reconcile_usage


class GraderTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_scenario(ROOT / "scenarios/continuity/changed-commitment.toml", 42)
        self.trace = [{"step_id": s["id"], "restart_verified": True}
                      if s.get("kind") == "restart" else
                      {"step_id": s["id"], "reply": json.dumps({"actions": s["expected_actions"]}),
                       "wall_secs": 0.5}
                      for s in self.spec["steps"]]

    def action(self):
        return copy.deepcopy(next(s["expected_actions"][0] for s in self.spec["steps"]
                                  if s.get("expected_actions")))

    def set_actions(self, step_id, actions):
        next(o for o in self.trace if o["step_id"] == step_id)["reply"] = json.dumps({"actions": actions})

    def test_oracle_passes(self):
        score = score_scenario(self.spec, self.trace)
        self.assertTrue(score["passed"])
        self.assertEqual(score["response_latency_secs"], 0.5)

    def test_empty_replies_fail_despite_quiet_turns(self):
        self.set_actions("dependency-ready", [])
        score = score_scenario(self.spec, self.trace)
        self.assertFalse(score["passed"])
        self.assertEqual(score["obligation_completion_rate"], 0)

    def test_stale_revision_and_recipient_fail_independently(self):
        for field in ("revision", "recipient"):
            with self.subTest(field=field):
                action = self.action()
                action[field] = "obsolete"
                self.set_actions("dependency-ready", [action])
                score = score_scenario(self.spec, self.trace)
                self.assertFalse(score["passed"])
                self.assertEqual(score["stale_delivery_count"], 1)

    def test_cancelled_delivery_fails(self):
        action = self.action()
        action["project"] = self.spec["variables"]["cancelled_project"]
        self.set_actions("cancelled-ready", [action])
        score = score_scenario(self.spec, self.trace)
        self.assertFalse(score["passed"])
        self.assertEqual(score["cancelled_action_count"], 1)

    def test_duplicate_with_different_key_still_fails(self):
        action = self.action()
        action["delivery_key"] = "trying-a-new-key"
        self.set_actions("duplicate", [action])
        score = score_scenario(self.spec, self.trace)
        self.assertFalse(score["passed"])
        self.assertEqual(score["duplicate_delivery_count"], 1)

    def test_early_delivery_is_not_success(self):
        self.set_actions("accept", [self.action()])
        self.set_actions("dependency-ready", [])
        score = score_scenario(self.spec, self.trace)
        self.assertFalse(score["passed"])
        self.assertEqual(score["premature_delivery_count"], 1)
        self.assertEqual(score["obligation_completion_rate"], 0)

    def test_extra_action_at_eligible_event_fails(self):
        self.set_actions("dependency-ready", [self.action(), self.action()])
        score = score_scenario(self.spec, self.trace)
        self.assertFalse(score["passed"])
        self.assertEqual(score["forbidden_action_count"], 1)

    def test_wrong_delivery_key_fails(self):
        action = self.action()
        action["delivery_key"] = "wrong"
        self.set_actions("dependency-ready", [action])
        self.assertFalse(score_scenario(self.spec, self.trace)["passed"])

    def test_empty_truncated_reordered_and_extra_traces_fail(self):
        for trace in ([], self.trace[:-1], self.trace[::-1], self.trace + [self.trace[-1]]):
            with self.subTest(trace=trace):
                self.assertFalse(score_scenario(self.spec, trace)["passed"])

    def test_unverified_restart_fails(self):
        next(o for o in self.trace if o["step_id"] == "restart")["restart_verified"] = False
        self.assertFalse(score_scenario(self.spec, self.trace)["passed"])

    def test_invalid_protocol_cannot_count_as_quiet_success(self):
        for reply in ('done', '{"actions": []} extra', '{"actions": [], "passed": true}',
                      '{"actions": [null]}', '{"actions": {}}', '{"actions": [{"kind":"send_release"}]}'):
            with self.subTest(reply=reply):
                self.trace[-1]["reply"] = reply
                self.assertEqual(score_scenario(self.spec, self.trace)["protocol_error_count"], 1)
                self.assertFalse(score_scenario(self.spec, self.trace)["passed"])

    def test_seeded_variants_reproduce_and_change(self):
        path = ROOT / "scenarios/continuity/changed-commitment.toml"
        self.assertEqual(self.spec, load_scenario(path, 42))
        self.assertNotEqual(self.spec["variables"], load_scenario(path, 43)["variables"])

    def test_reports_are_based_on_reply_and_unknown_cost_stays_null(self):
        with tempfile.TemporaryDirectory() as temp:
            result = execute(self.spec, ValidationDriver(self.spec, True), Path(temp), "grader_self_test")
            self.assertTrue(result["metrics"]["passed"])
            self.assertIsNone(result["metrics"]["cost_usd_per_completed_obligation"])
            self.assertEqual(len((Path(temp) / "observations.jsonl").read_text().splitlines()), 8)

    def test_failures_and_cleanup_errors_are_recorded(self):
        class Broken(ValidationDriver):
            def restart(self):
                raise RuntimeError("restart failed")

            def close(self):
                raise RuntimeError("cleanup failed")
        with tempfile.TemporaryDirectory() as temp:
            result = execute(self.spec, Broken(self.spec, True), Path(temp), "grader_self_test")
            self.assertFalse(result["metrics"]["passed"])
            self.assertEqual(result["errors"], ["restart failed", "cleanup: cleanup failed"])

    def test_genesis_failure_retains_partial_metadata_and_usage(self):
        class FailedGenesis(ValidationDriver):
            metadata = {"model": "test-flash", "initialization_completed": False}

            def start(self):
                raise TimeoutError("genesis timed out")

            def telemetry(self):
                return {"cost_usd": 0.03, "input_tokens": 12000, "request_count": 4}

        with tempfile.TemporaryDirectory() as temp:
            result = execute(self.spec, FailedGenesis(self.spec, True), Path(temp), "model_run")
            self.assertFalse(result["metrics"]["passed"])
            self.assertFalse(result["driver"]["initialization_completed"])
            self.assertEqual(result["telemetry"]["request_count"], 4)
            self.assertIsNone(result["metrics"]["cost_usd_per_completed_obligation"])


class UsageTests(unittest.TestCase):
    def test_reconstructs_pre_restart_usage_and_deduplicates_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = [{"type": "message.v2", "role": "assistant", "message_id": str(i),
                     "role_metadata": {"Assistant": {"usage": {
                         "input": 1000, "output": 100, "cache_read_input_tokens": 800}}}}
                    for i in range(2)]
            (root / "session.jsonl").write_text("\n".join(map(json.dumps, [*rows, rows[0]])))
            result = reconcile_usage(root, {"request_count": 1},
                                     {"input_per_million": 0.14, "output_per_million": 0.28}, 0.0028)
            self.assertEqual(result["request_count"], 2)
            self.assertEqual(result["uncached_input_tokens"], 400)
            self.assertEqual(result["input_tokens"], 2000)
            self.assertFalse(result["quota_snapshot_request_count_matches"])
            self.assertAlmostEqual(result["cost_usd"], 0.00011648)
            unknown = reconcile_usage(root, {}, {"input_per_million": 0.14, "output_per_million": 0.28})
            self.assertIsNone(unknown["cost_usd"])

    def test_absent_trace_cannot_claim_complete_usage(self):
        with tempfile.TemporaryDirectory() as temp:
            result = reconcile_usage(Path(temp), {"request_count": 5, "cost_usd": 0.01}, {})
            self.assertFalse(result["usage_complete"])
            self.assertIsNone(result["cost_usd"])


class AdapterTests(unittest.TestCase):
    def test_missing_binary_fails_without_touching_keychain(self):
        with patch.dict(os.environ, {}, clear=True):
            driver = PekoDriver(Path("unused"), 600, 1)
            with self.assertRaisesRegex(ValueError, "PEKO_BIN"):
                driver.start()
            self.assertIsNone(driver.temp)

    def test_native_setup_is_isolated_and_records_both_binary_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "peko").write_text("cli")
            (root / "peko-daemon").write_text("daemon")
            calls = []
            def command(driver, *args, **kwargs):
                calls.append(args)
                if args[:2] == ("model", "show"):
                    return json.dumps({"modelId": "test-model", "spec": {"pricing": {
                        "input_per_million": 1, "output_per_million": 2}}})
                if args[:2] == ("daemon", "status"):
                    (Path(driver.temp.name) / ".peko/run/daemon.pid").write_text("12345")
                    return '{"ready": true, "running": true}'
                return "test version"
            with patch.dict(os.environ, {"PEKO_BIN": str(root / "peko"), "PEKO_API_KEY": "test-secret"}), \
                 patch.object(PekoDriver, "_command", command), \
                 patch.object(PekoDriver, "_stop_owned_daemon"):
                driver = PekoDriver(root, 600, 1)
                try:
                    metadata = driver.start()
                    self.assertNotEqual(driver.env["HOME"], os.environ.get("HOME"))
                    self.assertEqual(driver.env["PEKO_UNLOCK_METHOD"], "passphrase")
                    self.assertNotIn("PEKO_TEST_RESOLVER_BOOTSTRAP", driver.env)
                    self.assertIn('name = "continuity-bench"',
                                  (Path(driver.temp.name) / "seed.toml").read_text())
                    self.assertIn("request_count = 100", (Path(driver.temp.name) / "seed.toml").read_text())
                    self.assertEqual(len(metadata["cli_sha256"]), 64)
                    self.assertEqual(len(metadata["daemon_sha256"]), 64)
                    self.assertEqual(metadata["wire_model"], "test-model")
                    model_add = calls[0]
                    self.assertIn("--api-format", model_add)
                    self.assertIn("--base-url", model_add)
                    self.assertNotIn("--template", model_add)
                    self.assertNotIn("test-secret", driver._redact("test-secret"))
                    self.assertTrue(any(c[0] == "create" and "--detach" not in c for c in calls))
                finally:
                    driver.close()

    def test_explicit_endpoint_and_model_descriptor_reach_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("peko", "peko-daemon"):
                (root / name).touch()
            settings = {"PEKO_BIN": str(root / "peko"), "PEKO_API_KEY": "test-secret",
                        "PEKO_API_FORMAT": "anthropic_messages",
                        "PEKO_BASE_URL": "https://example.invalid/anthropic",
                        "PEKO_MODEL_NAME": "test-flash", "PEKO_MODEL_ID": "bench-flash",
                        "PEKO_MODEL_SPEC": '{"tool_support":"function_calling"}',
                        "PEKO_CONTEXT_WINDOW": "1048576", "PEKO_MAX_OUTPUT_TOKENS": "8192"}
            with patch.dict(os.environ, settings), \
                 patch.object(PekoDriver, "_command", return_value='{"spec": null}') as command, \
                 patch.object(PekoDriver, "_stop_owned_daemon"):
                driver = PekoDriver(root, 600, 1)
                try:
                    with self.assertRaisesRegex(ValueError, "pricing"):
                        driver.start()
                    args = command.call_args_list[0].args
                    for flag, value in (("--id", "bench-flash"), ("--model", "test-flash"),
                                        ("--base-url", settings["PEKO_BASE_URL"]),
                                        ("--spec", settings["PEKO_MODEL_SPEC"]),
                                        ("--context-window", "1048576"),
                                        ("--max-output-tokens", "8192")):
                        self.assertEqual(args[args.index(flag) + 1], value)
                finally:
                    driver.close()

    def test_unknown_pricing_refuses_before_create(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("peko", "peko-daemon"):
                (root / name).touch()
            with patch.dict(os.environ, {"PEKO_BIN": str(root / "peko"), "PEKO_API_KEY": "test-secret"}), \
                 patch.object(PekoDriver, "_command", return_value='{"spec": null}') as command, \
                 patch.object(PekoDriver, "_stop_owned_daemon"):
                driver = PekoDriver(root, 600, 1)
                try:
                    with self.assertRaisesRegex(ValueError, "pricing"):
                        driver.start()
                    self.assertEqual(command.call_count, 2)
                finally:
                    driver.close()

    def test_send_uses_new_final_channel_reply_instead_of_stream(self):
        driver = PekoDriver(Path("unused"), 600, 1)
        final = {"messages": [{"id": "reply-1", "sender": {"kind": "principal", "id": "did:test"},
                               "text": '{"actions": []}'}]}
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(driver, "_command", side_effect=["I'll remember this.\n...", json.dumps(final),
                                                          "more prose", json.dumps(final)]):
            driver.temp = type("Temp", (), {"name": temp})()
            self.assertEqual(parse_actions(driver.turn("event")), [])
            with self.assertRaisesRegex(ValueError, "new principal reply"):
                driver.turn("next event")


if __name__ == "__main__":
    unittest.main()
