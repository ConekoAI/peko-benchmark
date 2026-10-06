"""Opt-in request sizes and run-local HMAC fingerprints, never prompt text.

Fingerprints cannot be compared across runs: the random HMAC key is not saved.
Message-prefix counts describe exact wire-message reuse, not provider cache
entries or tokenizer output. Cache markers are measured separately from text.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets


def without_cache_markers(value):
    if isinstance(value, dict):
        return {k: without_cache_markers(v) for k, v in value.items() if k != "cache_control"}
    if isinstance(value, list):
        return [without_cache_markers(v) for v in value]
    return value


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


class PromptProfiler:
    def __init__(self, key=None):
        self.key = key if key is not None else secrets.token_bytes(32)
        self.previous = []

    def digest(self, value):
        return hmac.new(self.key, encoded(value), hashlib.sha256).hexdigest()

    def capture(self, payload, index):
        tools = without_cache_markers(payload.get("tools", []))
        system = without_cache_markers(payload.get("system", []))
        messages = [without_cache_markers(m) for m in payload.get("messages", [])]
        parameters = {k: v for k, v in payload.items()
                      if k not in {"tools", "system", "messages", "metadata", "stream"}}
        profile = {"version": 1, "fingerprint_algorithm": "run_local_hmac_sha256",
                   "tools_hash": self.digest(tools), "system_hash": self.digest(system),
                   "parameters_hash": self.digest(parameters),
                   "tool_count": len(tools), "tools_json_bytes": len(encoded(tools)),
                   "system_json_bytes": len(encoded(system)),
                   "messages_json_bytes": len(encoded(messages)),
                   "message_count": len(messages),
                   "messages": [{"role": m.get("role") if m.get("role") in {"user", "assistant"} else "other",
                                 "hash": self.digest(m),
                                 "json_bytes": len(encoded(m))} for m in messages]}
        markers = []
        for field in ("tools", "system", "messages"):
            items = payload.get(field, [])
            if not isinstance(items, list):
                continue
            for pos, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                if "cache_control" in item:
                    markers.append({"field": field, "item": pos})
                content = item.get("content", [])
                if isinstance(content, list):
                    markers.extend({"field": field, "item": pos, "block": b}
                                   for b, block in enumerate(content)
                                   if isinstance(block, dict) and "cache_control" in block)
        profile["cache_marker_locations"] = markers
        # Match against the best earlier request, not merely the previous call:
        # independent native sessions can interleave through the relay.
        best, count = None, -1
        for previous_index, previous in self.previous:
            if any(previous[k] != profile[k] for k in ("tools_hash", "system_hash", "parameters_hash")):
                continue
            common = 0
            for old, new in zip(previous["messages"], profile["messages"]):
                if old["hash"] != new["hash"]:
                    break
                common += 1
            if common >= count:
                best, count = (previous_index, previous), common
        profile["best_previous_request"] = best[0] if best else None
        profile["shared_message_prefix_count"] = max(count, 0)
        profile["shared_message_prefix_json_bytes"] = sum(
            m["json_bytes"] for m in profile["messages"][:max(count, 0)])
        profile["extends_previous_request"] = bool(best and count == best[1]["message_count"])
        self.previous.append((index, profile))
        return profile
