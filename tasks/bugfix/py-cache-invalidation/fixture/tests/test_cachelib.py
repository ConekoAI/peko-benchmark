import unittest

from cachelib import DictCache


class TestDictCache(unittest.TestCase):
    def test_set_get(self):
        c = DictCache()
        c.set("a", 1)
        self.assertEqual(c.get("a"), 1)

    def test_get_missing_returns_default(self):
        c = DictCache()
        self.assertIsNone(c.get("nope"))
        self.assertEqual(c.get("nope", 42), 42)

    def test_overwrite(self):
        c = DictCache()
        c.set("a", 1)
        c.set("a", 2)
        self.assertEqual(c.get("a"), 2)

    def test_len(self):
        c = DictCache()
        c.set("a", 1)
        c.set("b", 2)
        self.assertEqual(len(c), 2)

    def test_invalidate_removes_entries(self):
        c = DictCache()
        c.set("a", 1, tag="g1")
        c.set("b", 2, tag="g1")
        c.set("c", 3, tag="g2")
        dropped = c.invalidate("g1")
        self.assertEqual(dropped, 2)
        self.assertIsNone(c.get("a"), "invalidated key 'a' still served a value")
        self.assertIsNone(c.get("b"), "invalidated key 'b' still served a value")
        self.assertEqual(len(c), 1)

    def test_invalidate_leaves_other_tags(self):
        c = DictCache()
        c.set("a", 1, tag="g1")
        c.set("c", 3, tag="g2")
        c.invalidate("g1")
        self.assertEqual(c.get("c"), 3)

    def test_invalidate_unknown_tag_is_noop(self):
        c = DictCache()
        c.set("a", 1)
        self.assertEqual(c.invalidate("nope"), 0)
        self.assertEqual(c.get("a"), 1)

    def test_reset_after_invalidate(self):
        c = DictCache()
        c.set("a", 1, tag="g1")
        c.invalidate("g1")
        c.set("a", 99, tag="g1")
        self.assertEqual(c.get("a"), 99)


if __name__ == "__main__":
    unittest.main()
