#!/usr/bin/env python3
"""Read retained usage and optional prompt fingerprints; makes no model calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from continuity_proxy import summarize_calls


def analyze(run_dir):
    rows = [json.loads(line) for line in (run_dir / "provider-calls.jsonl").read_text().splitlines()]
    phases = {}
    for phase in sorted({r.get("phase", "unknown") for r in rows}):
        calls = [r for r in rows if r.get("phase", "unknown") == phase and r.get("forwarded")]
        usage = summarize_calls(calls)
        total = usage["input_tokens"] or 0
        usage["cache_read_fraction"] = (usage["cache_read_tokens"] or 0) / total if total else None
        completed = [c for c in calls if c.get("completed") and c.get("status") == 200
                     and "input_tokens" in c.get("usage", {}) and "output_tokens" in c.get("usage", {})]
        usage["zero_cache_read_calls"] = sum(not c["usage"].get("cache_read_input_tokens", 0) for c in completed)
        usage["incomplete_cache_usage_calls"] = len(calls) - len(completed)
        profiles = [c["prompt_profile"] for c in calls if "prompt_profile" in c]
        usage["profiled_calls"] = len(profiles)
        if profiles:
            usage["tool_catalog_variants"] = len({p["tools_hash"] for p in profiles})
            usage["system_variants"] = len({p["system_hash"] for p in profiles})
            usage["mean_tools_json_bytes"] = sum(p["tools_json_bytes"] for p in profiles) / len(profiles)
            usage["mean_system_json_bytes"] = sum(p["system_json_bytes"] for p in profiles) / len(profiles)
            usage["mean_messages_json_bytes"] = sum(p["messages_json_bytes"] for p in profiles) / len(profiles)
            usage["extends_an_earlier_request_calls"] = sum(p["extends_previous_request"] for p in profiles)
        phases[phase] = usage
    contexts, seen = [], set()
    for path in (run_dir / "runtime-traces").rglob("*.jsonl"):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("type") != "message.v2" or row.get("role") != "user":
                continue
            identifier = row.get("message_id") or row.get("id")
            if identifier in seen:
                continue
            seen.add(identifier)
            if (row.get("role_metadata", {}).get("User") or {}).get("source") != "hook":
                continue
            text = "".join(c.get("text", "") for c in row.get("content", []) if c.get("type") == "text")
            if text.startswith("<runtime-context>"):
                contexts.append(text)
    wire = [{"index": r["index"], "phase": r.get("phase"),
             "input_tokens": r.get("usage", {}).get("input_tokens"),
             "cache_read_input_tokens": r.get("usage", {}).get("cache_read_input_tokens", 0),
             "best_previous_request": r["prompt_profile"]["best_previous_request"],
             "shared_message_prefix_count": r["prompt_profile"]["shared_message_prefix_count"],
             "message_count": r["prompt_profile"]["message_count"],
             "extends_previous_request": r["prompt_profile"]["extends_previous_request"]}
            for r in rows if r.get("forwarded") and "prompt_profile" in r]
    return {"report_id": run_dir.name, "phases": phases, "wire_prefix_calls": wire,
            "peko_runtime_context": {"messages": len(contexts), "total_characters": sum(map(len, contexts)),
                "duplicate_session_context_messages": sum("## Session context\n" in t
                    and "## session_context\n" in t for t in contexts)},
            "limitations": ["Byte counts describe JSON size, not tokenizer counts.",
                "Hashes are keyed per run; variants cannot be compared across runs.",
                "Exact message-prefix reuse is not proof of a provider cache hit.",
                "Cache markers are excluded from fingerprints; string versus typed-block shapes remain distinct.",
                "Metadata, stream mode, HTTP headers and provider routing are outside prefix matching.",
                "Native runtime-context counts are Peko-only; absence for OpenClaw is not a zero-context claim."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps([analyze(path) for path in args.reports], indent=2))


if __name__ == "__main__":
    main()
