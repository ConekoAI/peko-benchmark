"""Finalization race checks without credentials or model calls."""
import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runner"))
from continuity_proxy import AnthropicRelay, summarize_calls
from responsibility import settled_telemetry


class RelayDrainTests(unittest.TestCase):
    def test_drain_freezes_admission_waits_for_active_call_and_preserves_timeout(self):
        received, release = threading.Event(), threading.Event()

        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                received.set()
                release.wait(5)
                data = b'{"usage":{"input_tokens":10,"output_tokens":5}}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with tempfile.TemporaryDirectory() as directory, ThreadPoolExecutor() as pool:
            relay = AnthropicRelay(f"http://127.0.0.1:{server.server_port}", "test-only",
                                   Path(directory) / "calls.jsonl", time.monotonic() + 30, .1)

            def request():
                req = urllib.request.Request(relay.url + "/v1/messages",
                    data=json.dumps({"model": "mimo-v2.6-flash", "max_tokens": 4096}).encode(),
                    headers={"x-api-key": relay.token})
                with urllib.request.urlopen(req, timeout=5) as response:
                    return json.load(response)

            try:
                pending = pool.submit(request)
                self.assertTrue(received.wait(2))
                self.assertFalse(relay.drain(0))
                self.assertFalse(relay.telemetry()["usage_complete"])
                self.assertIsNone(relay.telemetry()["cost_usd"])
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request()
                self.assertEqual(error.exception.code, 429)
                release.set()
                self.assertTrue(relay.drain(2))
                self.assertEqual(pending.result(timeout=2)["usage"]["output_tokens"], 5)
                totals = relay.telemetry()
                self.assertTrue(totals["usage_complete"])
                self.assertEqual(totals["request_count"], 1)
                self.assertEqual(totals["rejected_request_count"], 1)
                self.assertEqual(relay.records[1]["rejection"], "measurement ended")
            finally:
                release.set()
                relay.close()
                server.shutdown()
                server.server_close()

    def test_settled_snapshot_retains_late_partial_usage_and_fails_reconciliation(self):
        calls = [{"forwarded": True, "completed": True, "status": 200,
                  "usage": {"input_tokens": 10, "output_tokens": 5}},
                 {"forwarded": True, "completed": False, "status": 200,
                  "usage": {"input_tokens": 20, "output_tokens": 0}}]
        relay = type("Relay", (), {"telemetry": lambda _: summarize_calls(calls)})()
        native = {"request_count": 1, "uncached_input_tokens": 10, "output_tokens": 5,
                  "cache_read_tokens": 0, "cache_creation_tokens": 0}
        result = settled_telemetry(relay, {"uncached_input_tokens": 10,
                                          "native_usage": native, "native_usage_matches": True})
        self.assertEqual(result["uncached_input_tokens"], 30)
        self.assertEqual(result["native_usage"], native)
        self.assertFalse(result["usage_complete"])
        self.assertFalse(result["native_usage_matches"])
        self.assertIsNone(result["cost_usd"])

    def test_downstream_disconnect_does_not_discard_upstream_completion_usage(self):
        import socket
        import struct
        first, finish = threading.Event(), threading.Event()
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *_): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                self.wfile.write(b'data: {"type":"message_start","message":{"usage":{"input_tokens":10}}}\n\n');self.wfile.flush()
                first.set();finish.wait(5)
                events=[{'type':'message_delta','usage':{'output_tokens':5}}, {'type':'message_stop'}]
                for event in events:
                    self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode());self.wfile.flush()
        server=ThreadingHTTPServer(('127.0.0.1',0),Upstream)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        with tempfile.TemporaryDirectory() as folder:
            relay=AnthropicRelay(f'http://127.0.0.1:{server.server_port}','dummy',Path(folder)/'calls.jsonl',time.monotonic()+20,.1)
            client=socket.create_connection(('127.0.0.1',relay.server.server_port))
            try:
                body=b'{"model":"mimo-v2.6-flash","max_tokens":4096,"stream":true}'
                request=(f'POST /v1/messages HTTP/1.1\r\nHost: localhost\r\nx-api-key: {relay.token}\r\nContent-Length: {len(body)}\r\n\r\n').encode()+body
                client.sendall(request);self.assertTrue(first.wait(2));client.recv(4096)
                client.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('ii',1,0));client.close()
                finish.set();self.assertTrue(relay.drain(3))
                self.assertTrue(relay.records[0]['downstream_disconnected'])
                self.assertTrue(relay.telemetry()['usage_complete'])
                self.assertEqual(relay.telemetry()['output_tokens'],5)
            finally:
                client.close();finish.set();relay.close();server.shutdown();server.server_close()
