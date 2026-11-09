"""The collaboration benchmark's grader, without processes or model calls."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "runner"))
import collab_score as cs  # noqa: E402
from collab import channel_ids, group_of, sign_jwt  # noqa: E402


def post(author, text, at="2026-11-09T10:00:00+00:00", board=None):
    ev = {"kind": "posted", "author": author, "text": text, "at": at}
    if board:
        ev["board"] = board
    return ev


MAYA, NOAH = "user:local:local", "user:hub:noah"
JUNO, OTTO = "principal:local:juno", "principal:hub:otto"


class TitleRule(unittest.TestCase):
    def test_same_work_and_different_work(self):
        self.assertTrue(cs.similar("Fix even-length median in stats.py",
                                   "Fix even-length median in stats.py (prepare, push after review)"))
        self.assertTrue(cs.similar("Add unit test for median([])",
                                   "Add a unit test for median([]) (empty list)"))
        self.assertFalse(cs.similar("Review the median fix before it is pushed",
                                    "Fix even-length median in stats.py (prepare, push after review)"))
        self.assertFalse(cs.similar("", "anything"))


class PostStats(unittest.TestCase):
    def test_counts_repeats_raw_json_and_board_changes(self):
        events = [
            {"kind": "created", "at": "2026-11-09T09:00:00+00:00"},
            post(MAYA, "@juno run the tests"),
            post(JUNO, "board: juno took “x”", board={"op": "claim"}),
            post(JUNO, "Thanks, @otto."),
            post(OTTO, "Agreed."),
            post(JUNO, "Thanks,   @otto."),  # the same post again (loop)
            post(OTTO, '{"channel": "group:x", "events": []}'),
        ]
        stats = cs.post_stats(events)
        self.assertEqual(stats["human_posts"], 1)
        self.assertEqual(stats["peko_posts"], 4)
        self.assertEqual(stats["board_posts"], 1)
        self.assertEqual(stats["repeated_peko_posts"], 1)
        self.assertEqual(stats["raw_json_posts"], 1)
        self.assertEqual(stats["peko_posts_per_human_post"], 4.0)

    def test_a_window_counts_only_its_posts(self):
        events = [post(JUNO, "before", at="2026-11-09T10:00:00+00:00"),
                  post(JUNO, "inside", at="2026-11-09T10:05:00+00:00"),
                  post(JUNO, "after", at="2026-11-09T10:10:00+00:00")]
        stats = cs.post_stats(events, "2026-11-09T10:01:00+00:00", "2026-11-09T10:09:00+00:00")
        self.assertEqual(stats["peko_posts"], 1)


class Boards(unittest.TestCase):
    ITEMS = [
        {"id": "msg_1", "title": "Fix even-length median", "state": "doing", "claimant_name": "otto"},
        {"id": "msg_2", "title": "Fix even-length median in stats.py", "state": "blocked",
         "claimant_name": "juno"},
        {"id": "msg_3", "title": "Run the tests", "state": "done", "claimant_name": "juno"},
    ]

    def test_open_duplicates_are_found(self):
        self.assertEqual(len(cs.unresolved_duplicates(self.ITEMS)), 1)
        resolved = [dict(i, state="done") if i["id"] == "msg_1" else i for i in self.ITEMS]
        self.assertEqual(cs.unresolved_duplicates(resolved), [])

    def test_computers_agree_by_name_not_address(self):
        other = [dict(i, claimant="principal:local:otto-elsewhere") for i in self.ITEMS]
        self.assertTrue(cs.boards_agree(self.ITEMS, other))
        drifted = [dict(i, state="open") if i["id"] == "msg_2" else i for i in self.ITEMS]
        self.assertFalse(cs.boards_agree(self.ITEMS, drifted))


class Score(unittest.TestCase):
    def run_evidence(self, **over):
        evidence = {
            "milestones": {"group_formed": 20.0, "fix_pushed": 300.0},
            "group_events": [post(MAYA, "@juno go"), post(JUNO, "On it.")],
            "boards": {"pc1": Boards.ITEMS[2:], "pc2": Boards.ITEMS[2:]},
            "branches_pushed": ["fix-median"],
        }
        evidence.update(over)
        return cs.score(evidence)

    def test_a_clean_run_passes(self):
        result = self.run_evidence()
        self.assertTrue(result["pass"], result["failures"])

    def test_each_problem_fails_the_run(self):
        cases = {
            "milestone": {"milestones": {"group_formed": None}},
            "loop": {"group_events": [post(MAYA, "go"), post(JUNO, "Thanks."), post(JUNO, "Thanks.")]},
            "duplicates": {"boards": {"pc1": Boards.ITEMS, "pc2": Boards.ITEMS}},
            "disagree": {"boards": {"pc1": Boards.ITEMS[2:], "pc2": []}},
            "two branches": {"branches_pushed": ["fix-a", "fix-b"]},
            "chatty": {"group_events": [post(MAYA, "go")] + [post(JUNO, f"note {n}") for n in range(5)]},
        }
        for name, over in cases.items():
            with self.subTest(name):
                self.assertFalse(self.run_evidence(**over)["pass"])

    def test_the_report_names_the_failures(self):
        result = self.run_evidence(branches_pushed=["a", "b"])
        text = cs.report_markdown(result, {"run_id": "x"})
        self.assertIn("FAIL", text)
        self.assertIn("2 branches pushed", text)


class ChannelList(unittest.TestCase):
    def test_the_group_is_the_channel_that_is_not_a_dm(self):
        listing = '["dm_f6c2", "group:stats-team"]'
        self.assertEqual(channel_ids(listing), ["dm_f6c2", "group:stats-team"])
        self.assertEqual(group_of(listing), "group:stats-team")
        # Older builds answered with an object.
        self.assertEqual(group_of('{"principal": "p", "channels": ["chan_ab12"]}'), "chan_ab12")
        self.assertIsNone(group_of('["dm_only"]'))
        self.assertIsNone(group_of(""))


class Token(unittest.TestCase):
    def test_the_hub_token_is_a_signed_hs256_jwt(self):
        import base64, hashlib, hmac, json
        token = sign_jwt({"sub": "u1", "namespace": "maya"}, "s" * 32)
        head, body, sig = token.split(".")
        pad = lambda s: s + "=" * (-len(s) % 4)  # noqa: E731
        self.assertEqual(json.loads(base64.urlsafe_b64decode(pad(head)))["alg"], "HS256")
        self.assertEqual(json.loads(base64.urlsafe_b64decode(pad(body)))["sub"], "u1")
        expected = hmac.new(b"s" * 32, f"{head}.{body}".encode(), hashlib.sha256).digest()
        self.assertEqual(base64.urlsafe_b64decode(pad(sig)), expected)


if __name__ == "__main__":
    unittest.main()
