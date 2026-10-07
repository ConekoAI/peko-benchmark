"""OpenClaw adapter/accounting checks; no external provider calls."""
import json
import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runner"))
from continuity_openclaw import OpenClawDriver, export_transcripts, final_reply, transcript_usage
from continuity_proxy import AnthropicRelay, merge_usage, summarize_calls


class OpenClawTests(unittest.TestCase):
    def test_final_payload_is_positional_not_json_search(self):
        self.assertEqual(final_reply({"result": {"payloads": [{"text": "before"},
                          {"text": '{"actions": []}'}]}}), '{"actions": []}')
        self.assertEqual(final_reply({"payloads": [{"text": '{"actions": []}'},
                          {"text": "invalid final"}]}), "invalid final")
        with self.assertRaises(ValueError):
            final_reply({"ok": False, "final": '{"actions": []}'})
        with self.assertRaises(ValueError):
            final_reply({"status": "in_flight", "payloads": [{"text": "pending"}]})

    def test_missing_installation_refuses_before_allocating_state(self):
        with patch.dict(os.environ, {}, clear=True):
            driver = OpenClawDriver(Path("unused"), 600, 10)
            with self.assertRaisesRegex(ValueError, "OPENCLAW_ENTRY"):
                driver.start()
            self.assertIsNone(driver.temp)

    def test_setup_isolates_state_and_keeps_upstream_key_out_of_agent_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            entry=root/'openclaw.mjs'
            entry.touch()
            (root/'package.json').write_text('{"version":"2026.9.8"}')
            settings={'OPENCLAW_ENTRY':str(entry),'PEKO_API_KEY':'private-test-key',
                      'OPENAI_API_KEY':'unrelated-private-key','PEKO_MODEL_NAME':'mimo-v2.6-flash'}
            with patch.dict(os.environ,settings), \
                 patch.object(OpenClawDriver,'_command',return_value='test version'), \
                 patch.object(OpenClawDriver,'_start_gateway'):
                driver=OpenClawDriver(root,600,10)
                try:
                    driver.start()
                    self.assertNotEqual(driver.env['HOME'],os.environ.get('HOME'))
                    self.assertNotIn('PEKO_API_KEY',driver.env)
                    self.assertNotIn('OPENAI_API_KEY',driver.env)
                    config=json.loads((driver.state/'openclaw.json').read_text())
                    self.assertNotIn('private-test-key',json.dumps(config))
                    self.assertEqual(config['agents']['defaults']['model']['fallbacks'],[])
                    self.assertNotEqual(driver.env['OPENCLAW_BENCH_PROVIDER_TOKEN'],'private-test-key')
                finally:
                    driver.close()

    def test_cumulative_usage_delta_replaces_not_adds(self):
        usage = {}
        merge_usage(usage, {"type": "message_start", "message": {"usage": {
            "input_tokens": 100, "cache_read_input_tokens": 200, "output_tokens": 0}}})
        merge_usage(usage, {"type": "message_delta", "usage": {"output_tokens": 40}})
        merge_usage(usage, {"type": "message_delta", "usage": {"output_tokens": 50}})
        self.assertTrue(merge_usage(usage, {"type": "message_stop"}))
        result = summarize_calls([{"forwarded": True, "completed": True, "status": 200, "usage": usage}])
        self.assertTrue(result["usage_complete"])
        self.assertEqual(result["input_tokens"], 300)
        self.assertEqual(result["uncached_input_tokens"], 100)
        self.assertEqual(result["output_tokens"], 50)
        self.assertAlmostEqual(result["cost_usd"], .00002856)

    def test_unknown_or_partial_usage_does_not_claim_zero_cost(self):
        self.assertIsNone(summarize_calls([])["cost_usd"])
        partial = {"forwarded": True, "completed": False, "status": 200,
                   "usage": {"input_tokens": 100, "output_tokens": 20}}
        self.assertFalse(summarize_calls([partial])["usage_complete"])
        self.assertIsNone(summarize_calls([partial])["cost_usd"])
        partial.update(completed=True)
        partial["usage"]["cache_creation_input_tokens"] = 10
        self.assertIsNone(summarize_calls([partial])["cost_usd"])

    def test_invalid_usage_is_rejected(self):
        for bad in (-1, True, "100"):
            with self.assertRaises(ValueError):
                merge_usage({}, {"usage": {"input_tokens": bad}})

    def test_wrong_model_and_output_cap_never_reach_provider(self):
        import time
        import urllib.error
        with tempfile.TemporaryDirectory() as temp:
            relay = AnthropicRelay("https://example.invalid/anthropic", "secret-upstream-key",
                                    Path(temp) / "calls.jsonl", time.monotonic() + 60, 10)
            try:
                for body in ({"model": "wrong", "max_tokens": 8192},
                             {"model": "mimo-v2.6-flash", "max_tokens": 16384}):
                    request = urllib.request.Request(relay.url + "/v1/messages",
                        data=json.dumps(body).encode(), headers={"x-api-key": relay.token})
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(request)
                    self.assertEqual(caught.exception.code, 429)
                result = relay.telemetry()
                self.assertEqual(result["request_count"], 0)
                self.assertEqual(result["rejected_request_count"], 2)
                self.assertNotIn("secret-upstream-key", (Path(temp) / "calls.jsonl").read_text())
            finally:
                relay.close()

    def test_relay_preserves_payload_and_reconciles_stream_usage(self):
        import threading
        import time
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        received = []
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                received.append((self.path, self.headers['x-api-key'],
                                 self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                for event in ({'type':'message_start', 'message':{'usage':{'input_tokens':100,'output_tokens':0,'cache_read_input_tokens':200}}},
                              {'type':'message_delta','delta':{'stop_reason':'max_tokens'},'usage':{'output_tokens':50}},
                              {'type':'message_stop'}):
                    self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode())
        server = ThreadingHTTPServer(('127.0.0.1',0),Upstream)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with tempfile.TemporaryDirectory() as temp:
            relay = AnthropicRelay(f'http://127.0.0.1:{server.server_port}/anthropic',
                                   'upstream-test-key',Path(temp)/'calls.jsonl',time.monotonic()+60,10)
            try:
                body=json.dumps({'model':'mimo-v2.6-flash','max_tokens':8192,
                                 'messages':[{'role':'user','content':'test'}],'stream':True}).encode()
                req=urllib.request.Request(relay.url+'/v1/messages',data=body,headers={'x-api-key':relay.token})
                with urllib.request.urlopen(req) as response:
                    response.read()
                deadline=time.monotonic()+2
                while not relay.telemetry()['usage_complete'] and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertEqual(received,[('/anthropic/v1/messages','upstream-test-key',body)])
                self.assertEqual(relay.telemetry()['output_tokens'],50)
                self.assertEqual(relay.telemetry()['input_tokens'],300)
                self.assertTrue(relay.telemetry()['usage_complete'])
                self.assertEqual(relay.records[0]['upstream_stop_reason'],'max_tokens')
                saved=json.loads((Path(temp)/'calls.jsonl').read_text().splitlines()[0])
                self.assertEqual(saved['upstream_stop_reason'],'max_tokens')
                self.assertNotIn('upstream-test-key',(Path(temp)/'calls.jsonl').read_text())
            finally:
                relay.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_nonstream_stop_reason_is_preserved_without_inferring_token_limit(self):
        import threading
        import time
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        response={'stop_reason':'tool_use','usage':{'input_tokens':10,'output_tokens':4096},
                  'content':[{'type':'tool_use','id':'empty','name':'Write','input':{}}]}
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                body=json.dumps(response).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
                self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Upstream)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        with tempfile.TemporaryDirectory() as temp:
            relay=AnthropicRelay(f'http://127.0.0.1:{server.server_port}','test-only',
                                Path(temp)/'calls.jsonl',time.monotonic()+20,.1)
            try:
                payload={'model':'mimo-v2.6-flash','max_tokens':4096,'stream':False}
                request=urllib.request.Request(relay.url+'/v1/messages',data=json.dumps(payload).encode(),
                                               headers={'x-api-key':relay.token})
                with urllib.request.urlopen(request) as result:
                    self.assertEqual(json.loads(result.read()),response)
                self.assertTrue(relay.drain(2))
                self.assertEqual(relay.records[0]['upstream_stop_reason'],'tool_use')
                self.assertEqual(relay.records[0]['usage']['output_tokens'],4096)
            finally:
                relay.close();server.shutdown();server.server_close();thread.join(2)

    def test_native_export_omits_auth_tables_and_preserves_compressed_events(self):
        import base64
        import shutil
        import sqlite3
        import subprocess
        node=shutil.which('node')
        if not node:
            self.skipTest('Node.js required for native compressed transcript export')
        event={'type':'message','message':{'role':'assistant','usage':{
            'input':100,'output':50,'cacheRead':200,'cacheWrite':0}}}
        script="const z=require('node:zlib');process.stdout.write(z.zstdCompressSync(Buffer.from(process.argv[1])).toString('base64'));"
        compressed=base64.b64decode(subprocess.check_output([node,'-e',script,json.dumps(event)],text=True))
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'agent.sqlite'
            with sqlite3.connect(source) as db:
                db.execute('create table transcript_events(session_id text,seq integer,event_json text,event_zstd blob)')
                db.execute('insert into transcript_events values(?,?,?,?)',('s',1,None,compressed))
                db.execute('create table auth_profile_store(secret text)')
                db.execute("insert into auth_profile_store values('not-for-export')")
            target=Path(temp)/'transcripts.jsonl'
            rows=export_transcripts(source,target,node,lambda x:x)
            self.assertNotIn('not-for-export',target.read_text())
            self.assertEqual(rows[0]['event'],event)
            self.assertEqual(transcript_usage(rows)['cache_read_tokens'],200)


if __name__ == "__main__":
    unittest.main()
