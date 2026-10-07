"""Common action boundary v1: caller-declared checks and transactional effects.

The service sees public current state, NOT hidden owner obligations or future
changes. It cannot certify an agent's recipient, cancellation or time threshold.
SQLite receipts are the simulated external effects; the ledger is audit only.
"""
import json
import math
import sqlite3
from contextlib import contextmanager

VERSION = 1


class ActionService:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS effects (receipt INTEGER PRIMARY KEY AUTOINCREMENT, '
                       'action_key TEXT UNIQUE NOT NULL, envelope TEXT NOT NULL, response TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def validate(envelope):
        if not isinstance(envelope, dict) or set(envelope) != {'action', 'preconditions'}:
            return 'expected action and preconditions envelope'
        action, pre = envelope['action'], envelope['preconditions']
        if not isinstance(action, dict) or not isinstance(pre, dict):
            return 'action and preconditions must be objects'
        kind = action.get('kind')
        fields = ({'kind','project','revision','recipient','delivery_key'} if kind=='send_release' else
                  {'kind','project','reason'} if kind=='request_input' else set())
        if not fields or set(action) != fields or any(not isinstance(action[k], str) or not action[k] for k in fields):
            return 'invalid operational action schema'
        if kind=='request_input' and action['reason']!='dependency_blocked':
            return 'invalid request_input reason'
        keys={'watch_active','dependency'} | ({'not_before'} if kind=='request_input' else set())
        if set(pre)!=keys or pre['watch_active'] is not True or not isinstance(pre['dependency'],dict):
            return 'invalid preconditions schema'
        dependency=pre['dependency']
        if set(dependency)!={'ready','revision'} or dependency['ready'] is not (kind=='send_release') or not isinstance(dependency['revision'],str):
            return 'explicit dependency ready and revision required'
        if kind=='send_release' and dependency['revision']!=action['revision']:
            return 'action revision must match declared dependency'
        if kind=='request_input':
            threshold=pre['not_before']
            if isinstance(threshold,bool) or not isinstance(threshold,(int,float)) or not math.isfinite(threshold) or threshold<0:
                return 'not_before must be finite nonnegative seconds'
        return None

    def submit(self, envelope, state):
        error=self.validate(envelope)
        if error: return 400, {'accepted':False,'effect_applied':False,'error':error}
        action, pre=envelope['action'],envelope['preconditions']
        key=('send_release:'+action['delivery_key'] if action['kind']=='send_release' else 'request_input:'+action['project'])
        encoded=json.dumps(envelope,sort_keys=True,separators=(',',':'))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing=db.execute('SELECT envelope,response FROM effects WHERE action_key=?',(key,)).fetchone()
            if existing:
                if existing[0]!=encoded:
                    return 409,{'accepted':False,'effect_applied':False,'error':'idempotency key conflicts with committed payload','action_key':key}
                return 200,json.loads(existing[1]) | {'effect_applied':False,'replayed':True}
            dependency=state['dependencies'].get(action['project'])
            eligible=(state['watch_active'] and dependency==pre['dependency']
                      and (action['kind']=='send_release' or state['elapsed_secs']>=pre['not_before']))
            if not eligible:
                return 412,{'accepted':False,'effect_applied':False,'error':'declared preconditions not satisfied','action_key':key}
            cursor=db.execute('INSERT INTO effects(action_key,envelope,response) VALUES(?,?,?)',(key,encoded,'{}'))
            response={'accepted':True,'recorded':True,'effect_applied':True,'replayed':False,
                      'receipt':cursor.lastrowid,'action_key':key,'action':action,
                      'committed_elapsed_secs':state['elapsed_secs']}
            db.execute('UPDATE effects SET response=? WHERE receipt=?',(json.dumps(response),cursor.lastrowid))
            return 200,response

    def receipts(self):
        with self.connect() as db:
            return [json.loads(row[0]) | {'effect_applied':False} for row in db.execute('SELECT response FROM effects ORDER BY receipt')]


def prompt(url):
    return ('Common action service v1. Operational POST /actions uses an envelope: '
            '{"action":<release or blocked-input object>,"preconditions":{"watch_active":true,'
            '"dependency":{"ready":true,"revision":"..."}}}. For request_input set ready=false and add '
            '"not_before":<owner specified blocked_at seconds> in preconditions. '
            'Take dependency revision/readiness from GET /world. The service checks declared conditions '
            'against current state. It does not know owner commitments; you must enforce recipient, '
            'revision, cancellation, deadline and the correct blocked_at yourself. '
            'Idempotency is send_release:<delivery_key> or request_input:<project>. '
            '200 accepted=true yields a durable receipt; an identical committed envelope returns that receipt '
            'with replayed=true, effect_applied=false. A different payload under its committed key returns 409. '
            '400 is invalid schema; 412 means declared conditions are not currently satisfied; neither applies an effect. '
            f'GET {url}/receipts returns committed receipts for reconciliation after an uncertain result or restart. '
            'Read receipts before retrying uncertain writes; never invent a new key to force redelivery. '
            'Memory probes continue to POST the plain memory object. A receipt proves a committed simulated '
            'effect, not correctness against owner requirements. ')
