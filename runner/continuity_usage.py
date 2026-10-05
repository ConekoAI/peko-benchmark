"""Reconcile Peko message.v2 usage with the final daemon quota snapshot.

The current engine stores cache-inclusive input in assistant role metadata.
The quota stream charges wire input separately from cache tokens. This reader
keeps both views and never calls a final post-restart snapshot a lifetime total.
"""
from __future__ import annotations

import json
from pathlib import Path


def reconcile_usage(session_root: Path, quota: dict, pricing: dict,
                    cache_read_rate: float | None = None) -> dict:
    totals = {k: 0 for k in ("input", "output", "cache_read_input_tokens",
                             "cache_creation_input_tokens")}
    seen = set()
    calls = 0
    for path in sorted(session_root.rglob("*.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("type") != "message.v2" or row.get("role") != "assistant":
                continue
            usage = (row.get("role_metadata", {}).get("Assistant") or {}).get("usage")
            if not usage:
                continue
            identifier = row.get("message_id") or row.get("id")
            if not identifier:
                raise ValueError("usage-bearing assistant record has no identifier")
            if identifier in seen:
                continue
            seen.add(identifier)
            calls += 1
            for key in totals:
                value = usage.get(key, 0) or 0
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"invalid persisted token count: {key}")
                totals[key] += value
    if not calls:
        return {"usage_source": "quota_snapshot_only", "usage_complete": False,
                "cost_usd": None, "quota_snapshot": quota}
    uncached = totals["input"] - totals["cache_read_input_tokens"] - totals["cache_creation_input_tokens"]
    if uncached < 0:
        raise ValueError("cache tokens exceed cache-inclusive persisted input")
    cost = (uncached * pricing["input_per_million"]
            + totals["output"] * pricing["output_per_million"]) / 1e6
    # Cache-write pricing is not configured; don't fabricate a full cost.
    if totals["cache_creation_input_tokens"] or (totals["cache_read_input_tokens"] and cache_read_rate is None):
        cost = None
    elif cache_read_rate is not None:
        cost += totals["cache_read_input_tokens"] * cache_read_rate / 1e6
    return {"usage_source": "persisted_assistant_usage", "usage_complete": True,
            "cost_usd": cost, "input_tokens": totals["input"],
            "uncached_input_tokens": uncached, "output_tokens": totals["output"],
            "request_count": calls, "cache_read_tokens": totals["cache_read_input_tokens"],
            "cache_creation_tokens": totals["cache_creation_input_tokens"],
            "quota_snapshot": quota,
            "quota_snapshot_request_count_matches": calls == quota.get("request_count")}
