import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'runner'))
from tool_surface import catalog, results, StreamTools


class SurfaceTests(unittest.TestCase):
    def test_wire_name_and_argument_mismatch_preserved_without_values(self):
        tools=catalog({'tools':[{'name':'Edit','input_schema':{'type':'object','required':['file_path','old_string','new_string'],
                                                               'properties':{'file_path':{'type':'string'}}}}]})
        capture=StreamTools(tools)
        capture.event({'type':'content_block_start','index':0,'content_block':{'type':'tool_use','id':'c1','name':'Edit','input':{}}})
        capture.event({'type':'content_block_delta','index':0,'delta':{'type':'input_json_delta','partial_json':'{"command":"SECRET_ARG"}'}})
        capture.event({'type':'content_block_stop','index':0})
        row=capture.evidence()[0]
        self.assertEqual(row['name'],'Edit')
        self.assertEqual(row['argument_keys'],['command'])
        self.assertEqual(row['missing_required'],['file_path','new_string','old_string'])
        self.assertTrue(row['arguments_complete'])
        self.assertNotIn('SECRET_ARG',json.dumps(row))
        request={'messages':[{'role':'user','content':[{'type':'tool_result','tool_use_id':'c1','is_error':True,'content':'SECRET_RESULT'}]}]}
        proof=results(request)
        self.assertTrue(proof[0]['is_error']);self.assertEqual(proof[0]['id'],'c1')
        self.assertNotIn('SECRET_RESULT',json.dumps(proof))

    def test_truncated_arguments_do_not_look_complete(self):
        c=StreamTools({})
        c.event({'type':'content_block_start','index':0,'content_block':{'type':'tool_use','id':'c1','name':'Bash','input':{}}})
        c.event({'type':'content_block_delta','index':0,'delta':{'type':'input_json_delta','partial_json':'{"command":'}})
        self.assertFalse(c.evidence()[0]['arguments_complete'])
        self.assertTrue(c.evidence()[0]['malformed_arguments'])

    def test_attribution_requires_matching_wire_native_intent_and_result(self):
        import tempfile
        from tool_surface import attribution,digest
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'runtime-traces').mkdir()
            native=[{'event':'tool.call'}, {'role':'assistant','content':[{'type':'tool_call','id':'c1','name':'Edit','arguments':{'command':'test'}}]},
                    {'role':'user','content':[{'type':'tool_result','tool_call_id':'c1','is_error':True}]}]
            (root/'runtime-traces/session.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in native))
            call={'id':'c1','name':'Edit','arguments_sha256':digest({'command':'test'}),
                  'advertised':True,'missing_required':['file_path'],'arguments_complete':True}
            rows=[{'index':1,'response_tool_calls':[call]}]
            self.assertEqual(attribution(root,rows)['calls'][0]['category'],'model_missing_required_argument')
            native[2]['content'][0]['is_error']=False
            (root/'runtime-traces/session.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in native))
            self.assertEqual(attribution(root,rows)['calls'][0]['category'],'accepted_noncanonical_arguments')
            call['arguments_sha256']=digest({'command':'changed'})
            self.assertEqual(attribution(root,rows)['calls'][0]['category'],'unresolved')

    def test_cross_stream_arguments_are_not_attributed_to_model(self):
        import tempfile
        from tool_surface import attribution,digest
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'runtime-traces').mkdir()
            native=[{'role':'assistant','content':[{'type':'tool_call','id':'read','name':'Read','arguments':{'command':'journal'}}]},
                    {'role':'user','content':[{'type':'tool_result','tool_call_id':'read','is_error':True}]}]
            (root/'runtime-traces/session.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in native))
            calls=[{'index':1,'response_tool_calls':[{'id':'bash','name':'Bash','arguments_sha256':digest({'command':'journal'}),'advertised':True,'missing_required':[]}]},
                   {'index':2,'response_tool_calls':[{'id':'read','name':'Read','arguments_sha256':digest({'file_path':'table'}),'advertised':True,'missing_required':[]}]}]
            proof=attribution(root,calls)['calls'][1]
            self.assertEqual(proof['category'],'native_arguments_substituted')
            self.assertEqual(proof['argument_sources'],[{'request_index':1,'id':'bash','name':'Bash'}])
