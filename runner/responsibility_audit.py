"""Detect native messaging attempts outside the simulator during the watch."""
import datetime as dt
import json
from pathlib import Path


def timestamp(value):
    if isinstance(value, (int, float)):
        return value / 1000 if value > 10_000_000_000 else value
    if isinstance(value, str):
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    return None


def native_outbound_attempts(run_dir: Path, start: float, end: float) -> list[dict]:
    found = {}
    for source in (run_dir / "runtime-traces").rglob("*.jsonl"):
        for line in source.read_text().splitlines():
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            event = row.get("event", row)
            if not isinstance(event, dict):
                continue
            message = event.get("message", event)
            if not isinstance(message, dict):
                continue
            if message.get("role") != "assistant":
                continue
            at = timestamp(event.get("ts", message.get("timestamp", event.get("timestamp"))))
            if at is None or not start <= at <= end:
                continue
            for block in message.get("content", []):
                name = block.get("name")
                arguments = block.get("arguments", {})
                if (block.get("type") in {"tool_call", "toolCall"}
                    and (name == "ChannelSend" or (name == "message"
                         and arguments.get("action", "send") in {"send", "reply", "broadcast"}))):
                    key = block.get("id") or json.dumps(block, sort_keys=True)
                    found[key] = {"time": at, "tool": name, "source": str(source.relative_to(run_dir))}
    return list(found.values())
