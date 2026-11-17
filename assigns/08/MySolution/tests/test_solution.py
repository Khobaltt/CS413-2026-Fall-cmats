"""Run from assigns/08: python3 -m unittest discover -s MySolution/tests -v."""

# Shared fixtures and independent reference search 
import sys
import json
import math
import threading
import unittest
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import solver
from solver import L
from service import QueensService
from dispatcher import dispatch
from errors import RpcError
from app import Server, decode

def reference(size):
    """Independent direct-style test oracle; never used by the application."""
    def search(board):
        row = len(board)
        if row == size:
            yield {'event': 'solution', 'board': board[:]}
            return
        for column in range(size):
            yield {'event': 'try', 'row': row, 'column': column, 'board': board[:]}
            safe = all(column != previous and abs(column-previous) != row-r
                       for r, previous in enumerate(board))
            if safe:
                yield {'event': 'place', 'row': row, 'column': column, 'board': board+[column]}
                yield from search(board+[column])
                yield {'event': 'backtrack', 'row': row, 'column': column, 'board': board[:]}
            else:
                yield {'event': 'reject', 'row': row, 'column': column, 'board': board[:]}
    yield from search([])
    yield {'event': 'done'}

def collect(size):
    current = solver.open_stream(size)
    while True:
        node = solver.force(current)
        if not node.is_cons:
            return
        yield solver.event_json(node.head)
        current = node.tail

class SolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        solver.program()  # Includes successful LAMBDA3 type checking.

    # Exercise real LAMBDA3 safety continuations
    def safe(self, column, board):
        items = L.fnlist_nil()
        for value in board:
            items = L.fnlist_cons(L.D0Vint(value), items)
        env = L.ENVnil()
        for name, value in [('safe', solver.program().arg1[1]),
                            ('board', L.D0Vlist(items)), ('column', L.D0Vint(column))]:
            env = L.ENVcns(name, value, env)
        expression = L.d0exp_parse('safe(column, 1, board, '
            'lam (u: unit) => lazy_make(lam (v: unit) => stcn_cons((1,0,0,list_nil()), '
            'lazy_make(lam (w: unit) => stcn_nil()))), '
            'lam (u: unit) => lazy_make(lam (v: unit) => stcn_cons((0,0,0,list_nil()), '
            'lazy_make(lam (w: unit) => stcn_nil()))))')
        return solver.force(L.d0exp_evaluate(expression, env)).head.arg1[0].arg1 == 1

    def test_safety_column_diagonals_and_safe(self):
        self.assertFalse(self.safe(2, [2]))
        self.assertFalse(self.safe(1, [2]))
        self.assertFalse(self.safe(3, [2]))
        self.assertTrue(self.safe(0, [2]))
        self.assertFalse(self.safe(0, [2, 3]))  # Conflict two rows away.
        self.assertTrue(self.safe(0, []))

    def test_four_exact_trace_cps_resumption_and_snapshots(self):
        events = list(collect(4))
        self.assertEqual(events, list(reference(4)))
        self.assertEqual({e['event'] for e in events},
                         {'try','place','reject','backtrack','solution','done'})
        self.assertEqual([e['board'] for e in events if e['event']=='solution'],
                         [[1,3,0,2], [2,0,3,1]])
        for event in events:
            if 'row' in event:
                # A board contains exactly one column per previous row; extending
                # at len(board) structurally rules out a same-row placement.
                self.assertEqual(len(event['board']), event['row'] + (event['event']=='place'))
        self.assertEqual(events[-1], {'event':'done'})
        self.assertEqual(sum(e['event']=='done' for e in events), 1)

    def test_eight_all_92_valid_unique_deterministic(self):
        solutions = []
        for actual, expected in zip(collect(8), reference(8), strict=True):
            self.assertEqual(actual, expected)
            if actual['event']=='solution':
                board = tuple(actual['board']); solutions.append(board)
                self.assertEqual(len(set(board)), 8)
                self.assertEqual(len({r-c for r,c in enumerate(board)}), 8)
                self.assertEqual(len({r+c for r,c in enumerate(board)}), 8)
        self.assertEqual(len(solutions), 92)
        self.assertEqual(len(set(solutions)), 92)
        self.assertEqual(solutions[0], (0,4,7,5,2,6,1,3))
        self.assertEqual([e['board'] for e in collect(4) if e['event']=='solution'],
                         [[1,3,0,2], [2,0,3,1]])

    # Observable actual evaluator work, not formatted lazy values
    def test_construct_open_and_bounded_prefix_do_not_run_later_work(self):
        original = L._d0val_apply
        counts = Counter()
        def observed(fn, arg):
            if isinstance(fn, L.D0Vfix):
                counts[fn.arg2.arg1] += 1
            return original(fn, arg)
        with patch.object(L, '_d0val_apply', side_effect=observed):
            for size in (4, 8, 9, 10):
                counts.clear()
                stream = solver.open_stream(size)
                self.assertEqual(counts['search'] + counts['safe'], 0)
                self.assertFalse(stream.evaluated)
                first = solver.force(stream)
                self.assertEqual(counts['search'], 1)
                self.assertEqual(counts['safe'], 0)
                self.assertFalse(first.tail.evaluated)
                second = solver.force(first.tail)
                self.assertEqual(solver.event_json(second.head)['event'], 'place')
                self.assertEqual(counts['search'], 1)
                self.assertEqual(counts['safe'], 1)
                self.assertFalse(second.tail.evaluated)
                before = counts.copy()
                self.assertIs(solver.force(stream), first)  # Memoized repeat.
                self.assertEqual(counts, before)

    def test_unrequested_failing_tail_and_final_empty(self):
        expr = L.d0exp_parse('lazy_make(lam (u: unit) => stcn_cons('
            '(0,0,0,list_nil()), lazy_make(lam (v: unit) => 1/0)))')
        stream = L.d0exp_evaluate(expr)
        first = solver.force(stream)
        self.assertFalse(first.tail.evaluated)
        with self.assertRaises(ZeroDivisionError):
            solver.force(first.tail)
        stream = solver.open_stream(4)
        while True:
            node = solver.force(stream)
            if solver.event_json(node.head)['event']=='done':
                self.assertFalse(node.tail.evaluated)
                self.assertFalse(solver.force(node.tail).is_cons)
                break
            stream = node.tail

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.service = QueensService(clock=lambda: self.now, lifetime=5)

    def open(self, size=4):
        return self.service.call('queens.open', {'size':size})['stream_id']

    def next(self, key, limit=1):
        return self.service.call('queens.next', {'stream_id':key, 'limit':limit})

    def assert_code(self, code, fn):
        with self.assertRaises(RpcError) as caught: fn()
        self.assertEqual(caught.exception.code, code)

    # Lifecycle, expiration, bounded forces, and atomic requests
    def test_limits_open_no_force_and_independent_streams(self):
        with patch.object(solver, 'force', wraps=solver.force) as observed:
            one, two = self.open(10), self.open(9)
            self.assertEqual(observed.call_count, 0)
            self.assertEqual(len(self.next(one)['events']), 1)
            self.assertEqual(observed.call_count, 1)
            self.assertEqual(len(self.next(one,32)['events']), 32)
            self.assertEqual(observed.call_count, 33)
            self.assertFalse(self.service.active[one].stream.evaluated)
            self.assertFalse(self.service.active[two].stream.evaluated)
            self.assertEqual(self.next(two)['events'][0], next(reference(9)))

    def test_exhaustion_repeated_next_close_unknown(self):
        key = self.open(); events=[]
        while True:
            result = self.next(key,32); events.extend(result['events'])
            self.assertLessEqual(len(result['events']),32)
            if result['done']: break
        self.assertEqual(events,list(reference(4)))
        self.assertNotIn(key,self.service.active)
        self.assertEqual(self.next(key),{'events':[],'done':True})
        self.assertEqual(self.service.call('queens.close',{'stream_id':key}),{'closed':True})
        self.assert_code(-32001,lambda:self.next(key))
        self.assert_code(-32001,lambda:self.next('unknown'))
        self.assert_code(-32001,lambda:self.service.call('queens.close',{'stream_id':key}))

    def test_close_active_and_expiration_cleanup(self):
        key=self.open(); self.service.call('queens.close',{'stream_id':key})
        self.assertNotIn(key,self.service.active)
        key=self.open(); self.now=4; self.next(key); self.now=8
        self.service.cleanup(); self.assertIn(key,self.service.active)
        self.now=9; self.service.cleanup(); self.assertNotIn(key,self.service.active)
        self.assert_code(-32001,lambda:self.next(key))
        key=self.open()
        while not self.next(key,32)['done']: pass
        self.now+=5; self.service.cleanup(); self.assertNotIn(key,self.service.completed)

    def test_capacity_and_exact_parameter_validation(self):
        self.service.capacity=1; key=self.open()
        self.assert_code(-32002,lambda:self.open())
        for value in (True,False,3,11,4.0,'8',None):
            self.assert_code(-32602,lambda:self.service.call('queens.open',{'size':value}))
        for value in (True,0,33,1.0,'1',None):
            self.assert_code(-32602,lambda:self.next(key,value))
        for method,params in [('queens.open',{}),('queens.open',{'size':8,'source':'x'}),
                              ('service.health',{'extra':1}),('queens.close',{'stream_id':[]}),
                              ('queens.next',{'stream_id':key}),('queens.open',[])]:
            self.assert_code(-32602,lambda:self.service.call(method,params))
        self.assert_code(-32601,lambda:self.service.call('evaluate',{}))

    def test_concurrent_next_no_duplicate_advancement(self):
        key=self.open()
        def consume(_):
            return self.next(key,32)['events']
        with ThreadPoolExecutor(max_workers=4) as pool:
            batches=list(pool.map(consume,range(20)))
        actual=Counter(json.dumps(e,sort_keys=True) for batch in batches for e in batch)
        expected=Counter(json.dumps(e,sort_keys=True) for e in reference(4))
        self.assertEqual(actual,expected)

class EnvelopeTests(unittest.TestCase):
    # Request validation, notifications, and safe failures
    def setUp(self): self.service=QueensService()
    def call(self, **changes):
        request={'jsonrpc':'2.0','method':'service.health','params':{},'id':1}
        request.update(changes); return dispatch(request,self.service)
    def test_ids(self):
        for value in (None,'abc',0,-2,1.25):
            self.assertEqual(self.call(id=value)['id'],value)
        for value in (True,[],{},math.inf,math.nan):
            self.assertEqual(self.call(id=value)['error']['code'],-32600)
    def test_invalid_envelopes_methods_params(self):
        for value in (None,1,[],[{}],{}, {'jsonrpc':'1.0','method':'x'},
                      {'jsonrpc':'2.0','method':2}):
            self.assertEqual(dispatch(value,self.service)['error']['code'],-32600)
        self.assertEqual(self.call(method='unknown')['error']['code'],-32601)
        self.assertEqual(self.call(params=[])['error']['code'],-32602)
        self.assertEqual(self.call(method='queens.next',params={'stream_id':'x','limit':1})['error']['code'],-32001)
    def test_notifications_and_hidden_internal_error(self):
        for method in ('service.health','unknown'):
            self.assertIsNone(dispatch({'jsonrpc':'2.0','method':method},self.service))
        with patch.object(self.service,'call',side_effect=RuntimeError('/private/path closure secret')):
            response=self.call(id='preserved')
        self.assertEqual(response,{'jsonrpc':'2.0','error':{'code':-32603,'message':'Internal error'},'id':'preserved'})
    def test_strict_json(self):
        for value in (b'{',b'{"x":NaN}',b'{"x":1,"x":2}',b'\xff'):
            with self.assertRaises((ValueError,UnicodeError)): decode(value)

class HTTPTests(unittest.TestCase):
    # Real local HTTP from open through all 92 solutions
    @classmethod
    def setUpClass(cls):
        cls.server=Server(('127.0.0.1',0))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start(); cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def post(self, request):
        body=request if isinstance(request,bytes) else json.dumps(request).encode()
        with urlopen(Request(self.url+'/rpc',data=body,headers={'Content-Type':'application/json'})) as response:
            data=response.read(); return response.status,json.loads(data) if data else None
    def rpc(self, method, params):
        status,response=self.post({'jsonrpc':'2.0','method':method,'params':params,'id':'http'})
        self.assertEqual(status,200); self.assertEqual(response['id'],'http')
        self.assertNotIn('error',response); return response['result']
    def test_full_eight_flow(self):
        key=self.rpc('queens.open',{'size':8})['stream_id']; solutions=[]; last=None; done_count=0
        while True:
            result=self.rpc('queens.next',{'stream_id':key,'limit':32})
            self.assertLessEqual(len(result['events']),32)
            for event in result['events']:
                last=event
                if event['event']=='solution': solutions.append(tuple(event['board']))
                if event['event']=='done': done_count+=1
            if result['done']: break
        self.assertEqual(len(solutions),92); self.assertEqual(len(set(solutions)),92)
        expected=[tuple(e['board']) for e in reference(8) if e['event']=='solution']
        self.assertEqual(solutions,expected)
        self.assertEqual(last,{'event':'done'}); self.assertEqual(done_count,1)
        self.assertEqual(self.rpc('queens.next',{'stream_id':key,'limit':1}),{'events':[],'done':True})
        self.assertEqual(self.rpc('queens.close',{'stream_id':key}),{'closed':True})
    def test_http_envelopes_notifications_parse_and_assets(self):
        self.assertEqual(self.post(b'{')[1]['error']['code'],-32700)
        self.assertEqual(self.post([])[1]['error']['code'],-32600)
        self.assertEqual(self.post({'jsonrpc':'2.0','method':'service.health'}),(204,None))
        self.assertEqual(self.post({'jsonrpc':'2.0','method':'unknown'}),(204,None))
        for path in ('/','/client.mjs','/style.css'):
            with urlopen(self.url+path) as response:
                self.assertEqual(response.status,200); self.assertTrue(response.read())
    def test_http_close_notification_executes(self):
        key=self.rpc('queens.open',{'size':4})['stream_id']
        self.assertEqual(self.post({'jsonrpc':'2.0','method':'queens.close','params':{'stream_id':key}}),(204,None))
        _,response=self.post({'jsonrpc':'2.0','method':'queens.next','params':{'stream_id':key,'limit':1},'id':7})
        self.assertEqual(response['error']['code'],-32001)

if __name__ == '__main__': unittest.main()
