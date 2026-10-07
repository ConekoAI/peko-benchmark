"""Loopback Anthropic relay: bounded calls, usage and value-free tool evidence.

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

from prompt_profile import PromptProfiler
from tool_surface import catalog, results, StreamTools, tool_call


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


def capture_stop_reason(record: dict, event: dict):
    """Retain protocol termination metadata, never infer it from token counts.

    Unknown strings are not persisted: they could contain arbitrary values.
    Missing reasons on historical or interrupted calls stay unmeasured.
    """
    reason = (event.get('stop_reason') or (event.get('delta') or {}).get('stop_reason')
              or (event.get('message') or {}).get('stop_reason'))
    if reason is not None:
        if reason in ('end_turn', 'max_tokens', 'stop_sequence', 'tool_use', 'pause_turn',
                      'refusal', 'model_context_window_exceeded'):
            record['upstream_stop_reason'] = reason
        else:
            record['upstream_stop_reason_unrecognized'] = True


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
                 policy: dict | None = None, phase=None, profile_prompt: bool = False):
        self.base_url, self.key, self.path = base_url.rstrip("/"), key, path
        self.deadline, self.budget_usd = deadline, budget_usd
        self.token = secrets.token_hex(24)
        self.records = []
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.admission_open = True
        self.active_requests = 0
        self.policy = policy
        self.phase = phase or (lambda: "continuity")
        self.profiler = PromptProfiler() if profile_prompt else None
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
                  "phase": self.phase(), "requested_decoding": requested,
                  "tool_catalog": catalog(payload), "request_tool_results": results(payload)}
        stream_tools = StreamTools(record["tool_catalog"])
        with self.lock:
            probe_policy = (self.policy or {}).get("probe_allowance")
            is_probe = record["phase"] == "probe"
            budget_records = ([r for r in self.records if (r.get("phase") == "probe") == is_probe]
                              if probe_policy else self.records)
            limits = probe_policy if probe_policy and is_probe else (self.policy or {})
            budget_limit = probe_policy["budget_usd"] if probe_policy and is_probe else self.budget_usd
            totals = summarize_calls(budget_records)
            # Full cost is unavailable without cache-write pricing; do not admit
            # another call once the provider has reported such tokens.
            projected_cost = sum((r.get("usage", {}).get("input_tokens", 0)
                                  + r.get("usage", {}).get("cache_creation_input_tokens", 0)) * .14
                                 + r.get("usage", {}).get("output_tokens", 0) * .28
                                 + r.get("usage", {}).get("cache_read_input_tokens", 0) * .0028
                                 for r in budget_records) / 1e6
            reason = None
            if not self.admission_open:
                reason = "measurement ended"
            elif payload.get("model") != "mimo-v2.6-flash":
                reason = "unexpected model"
            elif isinstance(payload.get("max_tokens"), bool) or not isinstance(payload.get("max_tokens"), int) or not 0 < payload["max_tokens"] <= 8192:
                reason = "output cap must be at most 8192"
            elif time.monotonic() >= self.deadline:
                reason = "scenario deadline reached"
            elif totals["cache_creation_tokens"]:
                reason = "cache-write pricing is unknown"
            elif totals["request_count"] >= limits.get("request_limit", 100) or (totals["uncached_input_tokens"] or 0) >= 2_000_000 or (totals["output_tokens"] or 0) >= limits.get("output_limit", 50_000) or projected_cost >= budget_limit:
                reason = "scenario usage budget reached"
            record["index"] = len(self.records) + 1
            record["forwarded"] = reason is None
            if reason:
                record["rejection"] = reason
            elif self.profiler:
                record["prompt_profile"] = self.profiler.capture(payload, record["index"])
            if record["forwarded"]:
                self.active_requests += 1
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
                            capture_stop_reason(record, event)
                            stream_tools.event(event)
                        if not record.get("downstream_disconnected"):
                            try:
                                handler.wfile.write(line)
                                handler.wfile.flush()
                            except (BrokenPipeError, ConnectionResetError):
                                # Keep consuming upstream to account for an interrupted native run.
                                # Completion/usage is evidence, not proof the client received it.
                                record["downstream_disconnected"] = True
                else:
                    data = response.read()
                    if response.status == 200:
                        decoded = json.loads(data)
                        merge_usage(record["usage"], decoded)
                        capture_stop_reason(record, decoded)
                        record["response_tool_calls"] = [tool_call(b, record["tool_catalog"])
                            for b in decoded.get("content", []) if b.get("type") == "tool_use"]
                        record["completed"] = True
                    handler.wfile.write(data)
                    handler.wfile.flush()
                handler.close_connection = True
        except Exception as exc:
            # Do not persist exception strings that could include credentials.
            record["transport_error"] = type(exc).__name__
            handler.close_connection = True
        finally:
            if payload.get("stream"):
                record["response_tool_calls"] = stream_tools.evidence()
            record["wall_secs"] = round(time.monotonic() - started, 3)
            with self.lock:
                self._save()
                self.active_requests -= 1
                self.condition.notify_all()

    def drain(self, timeout_secs: float = 30) -> bool:
        """End admission and wait boundedly for forwarded handlers to settle.

        Call only after measurement/probe work. A timeout does not imply full
        usage; interrupted or missing completion records remain incomplete.
        """
        with self.condition:
            self.admission_open = False
            wait_secs = max(0, min(timeout_secs, self.deadline - time.monotonic()))
            return self.condition.wait_for(lambda: self.active_requests == 0, wait_secs)

    def telemetry(self):
        with self.lock:
            return summarize_calls(self.records)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
