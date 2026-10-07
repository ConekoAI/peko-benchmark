"""Value-free provider/dispatcher evidence. Never persist prompt or argument values."""
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def catalog(payload):
    return {t['name']: {'schema_sha256': digest(t.get('input_schema', {})),
                       'required': t.get('input_schema', {}).get('required', []),
                       'properties': {k: v.get('type') for k, v in
                                      t.get('input_schema', {}).get('properties', {}).items()}}
            for t in payload.get('tools', []) if isinstance(t.get('name'), str)}


def tool_call(block, tools):
    args = block.get('input')
    name = block.get('name')
    schema = tools.get(name)
    keys = sorted(args) if isinstance(args, dict) else None
    return {'id': block.get('id'), 'name': name, 'argument_keys': keys,
            'arguments_sha256': digest(args), 'advertised': schema is not None,
            'missing_required': sorted(set(schema['required']) - set(keys or [])) if schema else None}


def results(payload):
    return [{'id': b.get('tool_use_id'), 'is_error': b.get('is_error', False),
             'content_sha256': digest(b.get('content'))}
            for m in payload.get('messages', []) for b in m.get('content', [])
            if isinstance(m.get('content'), list) and isinstance(b, dict) and b.get('type') == 'tool_result']


class StreamTools:
    def __init__(self, tools):
        self.tools, self.blocks = tools, {}

    def event(self, event):
        index = event.get('index')
        if event.get('type') == 'content_block_start':
            block = event.get('content_block', {})
            if block.get('type') == 'tool_use':
                self.blocks[index] = {'block': dict(block), 'fragments': '', 'stopped': False}
        elif event.get('type') == 'content_block_delta' and index in self.blocks:
            delta = event.get('delta', {})
            if delta.get('type') == 'input_json_delta':
                self.blocks[index]['fragments'] += delta.get('partial_json', '')
        elif event.get('type') == 'content_block_stop' and index in self.blocks:
            self.blocks[index]['stopped'] = True

    def evidence(self):
        evidence = []
        for row in self.blocks.values():
            block = dict(row['block'])
            try:
                if row['fragments']:
                    block['input'] = json.loads(row['fragments'])
                proof = tool_call(block, self.tools)
                proof['arguments_complete'] = row['stopped']
            except ValueError:
                proof = {'id': block.get('id'), 'name': block.get('name'),
                         'arguments_complete': False, 'malformed_arguments': True}
            evidence.append(proof)
        return evidence


def attribution(run_dir, records):
    """Join wire intent to persisted native intent/result; uncertainty is explicit.

    Root required keys are a partial schema check, not full JSON Schema validation.
    Tool IDs may be normalized; name AND argument hash must still match.
    Missing wire arguments do not establish whether generation, truncation or
    provider conversion caused them. Preserve observed termination separately.
    """
    from collections import Counter
    from pathlib import Path
    import re
    native, outcomes = {}, {}
    hashes = {}
    for record in records:
        for call in record.get("response_tool_calls", []):
            hashes.setdefault(call.get("arguments_sha256"), []).append({"request_index":record["index"], "id":call.get("id"), "name":call.get("name")})
    for path in (Path(run_dir)/'runtime-traces').rglob('*.jsonl'):
        for line in path.read_text().splitlines():
            row=json.loads(line)
            if not isinstance(row,dict): continue
            event=row.get('event',row)
            if not isinstance(event,dict): continue
            message=event.get('message',event)
            if not isinstance(message,dict): continue
            if message.get('role')=='toolResult':
                outcomes[message.get('toolCallId')]=bool(message.get('isError',False))
            for block in message.get('content',[]) if isinstance(message.get('content'),list) else []:
                if not isinstance(block,dict): continue
                if block.get('type') in ('tool_call','toolCall'):
                    native[block.get('id')]={'name':block.get('name'),
                        'arguments_sha256':digest(block.get('arguments',{})),
                        'source':str(path.relative_to(run_dir))}
                elif block.get('type')=='tool_result':
                    outcomes[block.get('tool_call_id')]=bool(block.get('is_error',False))
    evidence=[]
    for record in records:
        for call in record.get('response_tool_calls',[]):
            wire_id=call.get('id')
            native_id=wire_id if wire_id in native else re.sub('[^a-zA-Z0-9]','',wire_id or '')
            intent=native.get(native_id)
            identical=bool(intent and intent['name']==call.get('name') and
                           intent['arguments_sha256']==call.get('arguments_sha256'))
            error=outcomes.get(native_id)
            substituted = bool(intent and intent['arguments_sha256'] != call.get('arguments_sha256') and hashes.get(intent['arguments_sha256']))
            category=('native_arguments_substituted' if substituted else 'unresolved' if not identical or error is None or not call.get('arguments_complete',True) else
                      'wire_missing_required_argument' if error and call.get('advertised') and call.get('missing_required') else
                      'accepted_noncanonical_arguments' if call.get('advertised') and call.get('missing_required') else
                      'unadvertised_wire_tool_choice' if not call.get('advertised') else
                      'native_error_requires_investigation' if error else 'native_success')
            evidence.append({'request_index':record['index'],'wire_id':wire_id,'native_id':native_id,
                             'name':call.get('name'),'intent_preserved':identical,'native_is_error':error,
                             'missing_required':call.get('missing_required'),'category':category,
                             'upstream_stop_reason':record.get('upstream_stop_reason'),
                             'argument_sources':hashes.get(intent['arguments_sha256'],[]) if substituted else []})
    return {'version':3,'counts':dict(Counter(e['category'] for e in evidence)), 'calls':evidence,
            'limitation':'Checks root required keys and persisted dispatch results; missing wire keys do not distinguish model errors from output limits or provider conversion. Conditional/value constraints, side-effect truth and all advertised tools require further proof. Historical runs without wire evidence stay unresolved.'}
