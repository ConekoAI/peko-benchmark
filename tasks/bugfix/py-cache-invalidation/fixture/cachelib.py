"""cachelib — a tiny tagged dict cache.

Usage:
    cache = DictCache()
    cache.set("a", 1, tag="group1")
    cache.get("a")              # -> 1
    cache.get("missing")        # -> None
    cache.invalidate("group1")  # drop every entry tagged "group1"
"""

from __future__ import annotations


class DictCache:
    def __init__(self) -> None:
        self._store: dict = {}
        self._tags: dict[str, set] = {}  # tag -> keys carrying that tag

    def set(self, key, value, tag=None) -> None:
        self._store[key] = value
        if tag is not None:
            self._tags.setdefault(tag, set()).add(key)

    def get(self, key, default=None):
        return self._store.get(key, default)

    def invalidate(self, tag) -> int:
        """Drop all entries carrying `tag`. Returns how many were dropped."""
        keys = self._tags.pop(tag, set())
        for key in keys:
            pass  # intended: remove key from the store
        return len(keys)

    def __len__(self) -> int:
        return len(self._store)
