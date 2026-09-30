import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

import mdstats


class TestCounters(unittest.TestCase):
    def test_count_lines(self):
        self.assertEqual(mdstats.count_lines(""), 0)
        self.assertEqual(mdstats.count_lines("one\n"), 1)
        self.assertEqual(mdstats.count_lines("one\ntwo"), 2)

    def test_count_words(self):
        self.assertEqual(mdstats.count_words("hello world"), 2)
        self.assertEqual(mdstats.count_words(""), 0)

    def test_count_bytes(self):
        self.assertEqual(mdstats.count_bytes("abc"), 3)
        self.assertEqual(mdstats.count_bytes("é"), 2)


class TestCli(unittest.TestCase):
    def run_cli(self, argv, stdin=""):
        buf = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(stdin)), redirect_stdout(buf):
            rc = mdstats.main(argv)
        return rc, buf.getvalue()

    def test_stdin_default_all(self):
        rc, out = self.run_cli([], stdin="a b\nc\n")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "2\t3\t6 -\n")

    def test_words_only(self):
        rc, out = self.run_cli(["--words"], stdin="a b c")
        self.assertEqual(out, "3 -\n")

    def test_file_label(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False
        ) as fh:
            fh.write("one two\n")
            path = fh.name
        try:
            rc, out = self.run_cli(["--lines", path])
            self.assertEqual(out, f"1 {path}\n")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
