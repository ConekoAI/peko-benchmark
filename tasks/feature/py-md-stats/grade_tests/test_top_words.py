"""Hidden grading tests for the --top-words feature.

Copied into the workdir by grade.sh at grading time — the agent never
sees this file.
"""

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

import mdstats


def run_cli(argv, stdin=""):
    buf = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(buf):
        rc = mdstats.main(argv)
    return rc, buf.getvalue()


class TestTopWords(unittest.TestCase):
    def test_basic_ranking(self):
        rc, out = run_cli(["--top-words", "2"], stdin="b a b c a b\n")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "b\t3\na\t2\n")

    def test_ties_broken_alphabetically(self):
        _, out = run_cli(["--top-words", "3"], stdin="pear apple banana\n")
        self.assertEqual(out, "apple\t1\nbanana\t1\npear\t1\n")

    def test_lowercasing_and_punctuation(self):
        _, out = run_cli(["--top-words", "2"], stdin="Hello, HELLO! hello; world.\n")
        self.assertEqual(out, "hello\t3\nworld\t1\n")

    def test_fewer_distinct_than_n(self):
        _, out = run_cli(["--top-words", "5"], stdin="x x y\n")
        self.assertEqual(out, "x\t2\ny\t1\n")

    def test_composes_with_summary_flags(self):
        _, out = run_cli(["--words", "--top-words", "1"], stdin="a a b\n")
        self.assertEqual(out, "3 -\n" + "a\t2\n")

    def test_digits_are_word_chars(self):
        _, out = run_cli(["--top-words", "1"], stdin="ab12 ab12 xy\n")
        self.assertEqual(out, "ab12\t2\n")


if __name__ == "__main__":
    unittest.main()
