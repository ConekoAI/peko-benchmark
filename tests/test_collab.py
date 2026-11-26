"""The collaboration benchmark's grader, without processes or model calls."""
import json
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


def said(author, text, at, msg_id=None, reply_to=None):
    ev = post(author, text, at=at)
    if msg_id:
        ev["msg_id"] = msg_id
    if reply_to:
        ev["reply_to"] = reply_to
    return ev


def at(minute, second=0):
    return f"2026-11-26T10:{minute:02d}:{second:02d}+00:00"


class PekosTalkingToPekos(unittest.TestCase):
    """peko-runtime ADR-128: read from a run, not graded."""
    NAMES = {JUNO: "juno", OTTO: "otto"}
    LOG = [
        said(MAYA, "@juno ask otto which branch to use", at(0)),
        said(JUNO, "@otto which branch should Maya use?", at(1), msg_id="m1"),
        said(OTTO, "main is fine", at(2), msg_id="m2", reply_to="m1"),
        said(JUNO, "@Maya otto says main is fine", at(3), reply_to="m2"),
        said(MAYA, "thanks. @juno anything left?", at(10)),
        said(JUNO, "Nothing left on my side.", at(11)),
        said(NOAH, "@otto and you?", at(20)),
        said(OTTO, "@juno did you close the item?", at(21), msg_id="m3"),
        post(JUNO, "board: juno closed “x”", at=at(22), board={"op": "update"}),
        said(OTTO, "@juno one more thing, can you tag it?", at(23), msg_id="m4"),
    ]

    def test_an_exchange_is_a_run_of_peko_posts_where_one_addresses_another(self):
        x = cs.exchanges(self.LOG, self.NAMES, [])
        self.assertEqual((x["count"], x["longest"]), (2, 3))
        self.assertEqual([e["posts"] for e in x["list"]], [3, 2])
        self.assertEqual((x["ended_by_themselves"], x["held_by_a_limit"]), (2, 0))

    def test_an_exchange_is_held_when_a_limit_held_a_post_during_it(self):
        # The wake book writes `Z`; the log writes `+00:00`.
        x = cs.exchanges(self.LOG, self.NAMES, ["2026-11-26T10:21:30.5Z"])
        self.assertEqual([e["held"] for e in x["list"]], [False, True])
        self.assertEqual((x["ended_by_themselves"], x["held_by_a_limit"]), (1, 1))
        # A hold between two exchanges belongs to neither.
        outside = cs.exchanges(self.LOG, self.NAMES, ["2026-11-26T10:15:00Z", "not a time"])
        self.assertEqual(outside["held_by_a_limit"], 0)

    def test_who_a_post_addresses(self):
        by_id = {e["msg_id"]: e for e in self.LOG if e.get("msg_id")}
        who = [cs.addressee(e, by_id, self.NAMES) for e in self.LOG if cs.is_peko(e["author"])]
        # mention; reply; a report to Maya threaded onto otto's answer is hers;
        # no one; mention; a board change mentions no one; mention.
        self.assertEqual(who, [OTTO, JUNO, None, None, JUNO, None, JUNO])
        self.assertFalse(cs.mentions("email juno@example.com or @junos", "juno"))
        self.assertTrue(cs.mentions("ok @Juno.", "juno"))

    def test_a_post_to_a_peko_with_nothing_from_it_after(self):
        dropped = cs.unanswered(self.LOG, self.NAMES)
        # juno answered m3 with a board change; nothing came after m4.
        self.assertEqual([(d["from"], d["to"], d["at"]) for d in dropped], [("otto", "juno", at(23))])

    def test_session_counts(self):
        def row(role, *blocks):
            return json.dumps({"type": "message.v2", "role": role, "content": list(blocks)})

        def text(t):
            return {"type": "text", "text": t}

        send = {"type": "tool_call", "name": "ChannelSend", "arguments": {}}
        note = "\n(Another peko wrote this to you. Nothing you write is posted to the group unless …)"
        remind = "(Your last reply was not posted: another peko started that turn, so …)"
        session = "\n".join([
            json.dumps({"type": "session.created"}),
            row("user", text("user:local:local (id msg_1): @otto hi")),
            row("assistant", text("hello")),
            row("user", text("principal:hub:juno (id msg_2): @otto which branch?" + note)),
            row("user", text("<runtime-context>\n## Board\n</runtime-context>")),
            row("assistant", send),
            row("assistant", text("NO_REPLY")),
            row("user", text("principal:hub:juno (id msg_3): @otto thanks" + note)),
            row("assistant", text("Glad to help.")),
            row("user", text(remind)),
            row("assistant", send),
            row("assistant", text("NO_REPLY")),
            row("user", text("principal:hub:juno (id msg_4): @otto bye" + note)),
            row("assistant", text("Bye.")),
            row("user", text(remind)),
            row("assistant", text("NO_REPLY")),
            row("user", text("(While you were over your limit of wakes here, other pekos wrote these to you. …)")),
            row("user", text("(Other pekos wrote these to you here before you could be woken. …)")),
            row("user", text("[peko] Background work completed …")),
            row("user", text("📨 [Helper: ChannelRead] {\"events\": []}")),
            "not json",
        ])
        self.assertEqual(cs.session_counts(session), {
            "peko_started_turns": 3, "compiled_wakes": 2, "of_which_held": 1,
            "reminders": 2, "reminders_posted": 1, "watch_started_turns": 1,
        })

    def test_the_report_has_the_section_only_with_data(self):
        run = {"group_events": self.LOG, "peko_names": self.NAMES,
               "wakes": {"otto": {"spent": ["a", "b"], "holds": ["2026-11-26T10:21:30Z"], "held": []}},
               "sessions": {"otto": {"peko_started_turns": 2, "reminders": 1, "reminders_posted": 1}}}
        result = cs.score(run)
        report = cs.report_markdown(result, {})
        self.assertIn("## Pekos talking to pekos", report)
        self.assertIn("Exchanges between pekos: 2 (longest 3 posts); 1 ended by themselves, 1 held by a wake limit",
                      report)
        self.assertIn("otto: woken by other pekos 2 times; 1 posts held by its limit, 0 still held", report)
        self.assertIn("left a reply unposted 1 times and posted it when asked 1 times", report)
        self.assertIn("otto → juno", report)
        # Reading it never fails a run.
        self.assertNotIn("limit", " ".join(result["failures"]))


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
