"""Loopback Anthropic relay: unchanged payloads, bounded calls, usage-only evidence.

The upstream credential remains in the controller; the agent gets a disposable
relay token. This is an accounting adapter, not an adversarial security boundary.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def merge_usage(target: dict, event: dict) -> bool:
    """Anthropic start/delta usage is cumulative; later values replace earlier ones."""
    usage = event.get("usage") or (event.get("message") or {}).get("usage") or {}
    for key in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                "cache_creation_input_tokens"):
        if key in usage:
            value = usage[key]
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"invalid upstream usage: {key}")
            target[key] = value
    return event.get("type") == "message_stop"


def summarize_calls(records: list[dict]) -> dict:
    forwarded = [r for r in records if r.get("forwarded")]
    complete = bool(forwarded) and all(r.get("completed") and r.get("status") == 200
                                     and "input_tokens" in r.get("usage", {})
                                     and "output_tokens" in r.get("usage", {}) for r in forwarded)
    totals = {k: sum(r.get("usage", {}).get(k, 0) for r in forwarded) for k in (
        "input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
    inclusive = totals["input_tokens"] + totals["cache_read_input_tokens"] + totals["cache_creation_input_tokens"]
    cost = (totals["input_tokens"] * .14 + totals["output_tokens"] * .28
            + totals["cache_read_input_tokens"] * .0028) / 1e6
    return {"usage_source": "controller_observed_anthropic_usage", "usage_complete": complete,
            "request_count": len(forwarded), "rejected_request_count": len(records) - len(forwarded),
            "input_tokens": inclusive if forwarded else None,
            "uncached_input_tokens": totals["input_tokens"] if forwarded else None,
            "output_tokens": totals["output_tokens"] if forwarded else None,
            "cache_read_tokens": totals["cache_read_input_tokens"] if forwarded else None,
            "cache_creation_tokens": totals["cache_creation_input_tokens"] if forwarded else None,
            "cost_usd": cost if complete and not totals["cache_creation_input_tokens"] else None,
            "cost_basis": "payg_reference_not_subscription_charge",
            "pricing": {"input_per_million": .14, "output_per_million": .28,
                        "cache_read_per_million": .0028}}


class AnthropicRelay:
    def __init__(self, base_url: str, key: str, path: Path, deadline: float, budget_usd: float,
                 policy: dict | None = None, phase=None):
        self.base_url, self.key, self.path = base_url.rstrip("/"), key, path
        self.deadline, self.budget_usd = deadline, budget_usd
        self.token = secrets.token_hex(24)
        self.records = []
        self.lock = threading.Lock()
        self.policy = policy
        self.phase = phase or (lambda: "continuity")
        relay = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                relay.handle(self)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def _save(self):
        self.path.write_text("".join(json.dumps(r) + "\n" for r in self.records))

    def _refuse(self, handler, status: int, reason: str):
        data = json.dumps({"type": "error", "error": {"type": "invalid_request_error", "message": reason}}).encode()
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    def handle(self, handler):
        if handler.headers.get("x-api-key") != self.token and handler.headers.get("Authorization") != f"Bearer {self.token}":
            return self._refuse(handler, 401, "invalid relay token")
        if handler.path != "/v1/messages":
            return self._refuse(handler, 404, "relay supports only /v1/messages")
        size = int(handler.headers.get("Content-Length", "0"))
        if not 0 < size <= 20_000_000:
            return self._refuse(handler, 400, "invalid body size")
        body = handler.rfile.read(size)
        payload = json.loads(body)
        requested = {k: payload.get(k) for k in ("max_tokens", "thinking", "temperature")}
        # Optional, explicit common decoding policy for matched responsibility
        # runs. Default continuity traffic is still forwarded unchanged.
        if self.policy and payload.get("model") == "mimo-v2.6-flash":
            payload["max_tokens"] = self.policy["max_tokens"]
            payload["thinking"] = self.policy["thinking"]
            payload.pop("temperature", None)
            payload.pop("output_config", None)
            body = json.dumps(payload).encode()
        record = {"index": 0, "forwarded": False, "completed": False, "usage": {},
                  "model": payload.get("model"), "max_tokens": payload.get("max_tokens"),
                  "thinking": payload.get("thinking"), "temperature": payload.get("temperature"),
                  "stream": payload.get("stream"), "started_at": time.time(),
                  "phase": self.phase(), "requested_decoding": requested}
        with self.lock:
            totals = summarize_calls(self.records)
            # Full cost is unavailable without cache-write pricing; do not admit
            # another call once the provider has reported such tokens.
            projected_cost = sum((r.get("usage", {}).get("input_tokens", 0)
                                  + r.get("usage", {}).get("cache_creation_input_tokens", 0)) * .14
                                 + r.get("usage", {}).get("output_tokens", 0) * .28
                                 + r.get("usage", {}).get("cache_read_input_tokens", 0) * .0028
                                 for r in self.records) / 1e6
            reason = None
            if payload.get("model") != "mimo-v2.6-flash":
                reason = "unexpected model"
            elif isinstance(payload.get("max_tokens"), bool) or not isinstance(payload.get("max_tokens"), int) or not 0 < payload["max_tokens"] <= 8192:
                reason = "output cap must be at most 8192"
            elif time.monotonic() >= self.deadline:
                reason = "scenario deadline reached"
            elif totals["cache_creation_tokens"]:
                reason = "cache-write pricing is unknown"
            elif totals["request_count"] >= (self.policy or {}).get("request_limit", 100) or (totals["uncached_input_tokens"] or 0) >= 2_000_000 or (totals["output_tokens"] or 0) >= (self.policy or {}).get("output_limit", 50_000) or projected_cost >= self.budget_usd:
                reason = "scenario usage budget reached"
            record["index"] = len(self.records) + 1
            record["forwarded"] = reason is None
            if reason:
                record["rejection"] = reason
            self.records.append(record)
            self._save()
        if reason:
            return self._refuse(handler, 429, reason)
        started = time.monotonic()
        try:
            headers = {"Content-Type": "application/json", "x-api-key": self.key,
                       "anthropic-version": handler.headers.get("anthropic-version", "2023-06-01")}
            if handler.headers.get("anthropic-beta"):
                headers["anthropic-beta"] = handler.headers["anthropic-beta"]
            req = urllib.request.Request(self.base_url + handler.path, data=body, headers=headers)
            try:
                response = urllib.request.urlopen(req, timeout=max(1, min(180, self.deadline - time.monotonic())))
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                record["status"] = response.status
                handler.send_response(response.status)
                content_type = response.headers.get("Content-Type", "application/json")
                handler.send_header("Content-Type", content_type)
                handler.send_header("Connection", "close")
                handler.end_headers()
                if "text/event-stream" in content_type:
                    for line in response:
                        if line.startswith(b"data: ") and line.strip() != b"data: [DONE]":
                            event = json.loads(line[6:])
                            record["completed"] = merge_usage(record["usage"], event) or record["completed"]
                        handler.wfile.write(line)
                        handler.wfile.flush()
                else:
                    data = response.read()
                    if response.status == 200:
                        merge_usage(record["usage"], json.loads(data))
                        record["completed"] = True
                    handler.wfile.write(data)
                    handler.wfile.flush()
                handler.close_connection = True
        except Exception as exc:
            # Do not persist exception strings that could include credentials.
            record["transport_error"] = type(exc).__name__
            handler.close_connection = True
        finally:
            record["wall_secs"] = round(time.monotonic() - started, 3)
            with self.lock:
                self._save()

    def telemetry(self):
        with self.lock:
            return summarize_calls(self.records)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
