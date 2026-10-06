import base64
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
import lambda1 as L
from reader import read, InputError
from backend import LambdaBackend, compute
from model import Model, StateError, Result, Artifact, MAX_BYTES
from controller import Controller
from app import make_server
SAMPLES=Path(__file__).resolve().parents[1]/'samples'

def wait(c):
    end=time.monotonic()+5
    while c.state()['busy'] and time.monotonic()<end: time.sleep(.01)
    assert not c.state()['busy'], 'operation failed to finish'
    return c.state()['results'][-1]

class FreeVariables(unittest.TestCase):
    def test_every_constructor(self):
        cases=[('D0Eint(2)',set()),('D0Ebtf(True)',set()),('D0Evar("x")',{'x'}),
          ('D0Eop1("+1", D0Evar("x"))',{'x'}),
          ('D0Eop2("+", D0Evar("x"), D0Evar("x"))',{'x'}),
          ('D0Elam("x", D0Epair(D0Evar("x"), D0Evar("y")))',{'y'}),
          ('D0Efix("f", "x", D0Epair(D0Eapp(D0Evar("f"), D0Evar("x")), D0Evar("z")))',{'z'}),
          ('D0Eapp(D0Evar("f"), D0Evar("x"))',{'f','x'}),
          ('D0Eif0(D0Evar("c"), D0Evar("a"), D0Evar("b"))',{'c','a','b'}),
          ('D0Elet("x", D0Evar("x"), D0Epair(D0Evar("x"), D0Evar("y")))',{'x','y'}),
          ('D0Epair(D0Evar("x"), D0Evar("y"))',{'x','y'}),
          ('D0Epfst(D0Evar("p"))',{'p'}),('D0Epsnd(D0Evar("p"))',{'p'})]
        for source,expected in cases:
            with self.subTest(source=source):
                result=L.d0exp_fvset(read(source)); self.assertIsInstance(result,frozenset)
                self.assertEqual(result,frozenset(expected))
        with self.assertRaises(TypeError): L.d0exp_fvset(L.D0E000())
    def test_nested_shadowing_unused(self):
        for s in ['D0Elam("x", D0Elam("x", D0Evar("x")))',
                  'D0Elam("x", D0Elet("x", D0Evar("x"), D0Evar("x")))',
                  'D0Elam("unused", D0Eint(1))']:
            self.assertEqual(L.d0exp_fvset(read(s)),frozenset())
    def test_lint_does_not_evaluate(self):
        with patch.object(L,'d0exp_evaluate',side_effect=AssertionError('evaluated')):
            self.assertEqual(compute('lint','D0Eop2("/", D0Eint(1), D0Eint(0))')[0],'success')
        self.assertEqual(compute('lint','D0Epair(D0Evar("z"), D0Evar("a"))'),
                         ('language_error','Undeclared variables: a, z'))

class ReaderTests(unittest.TestCase):
    def test_comments_multiline_signed(self):
        self.assertEqual(read('# hello\nD0Eop2(\n"+", D0Eint(-2), # comment\nD0Eint(+4))').arg1.arg1,-2)
    def test_restricted_reader(self):
        for s in ['__import__("os").system("echo bad")','D0Eint(True)','D0Ebtf(1)',
                  'D0Elam(1, D0Eint(0))','D0Eint(arg1=3)','D0Eint(1,2)','D0Eint(1+2)',
                  'D0Eint(*[1])','42','D0Eint(1); D0Eint(2)','D0Epair(D0Eint(1), "bad")',
                  'D0Evar(None)','D0Eint(','[D0Eint(1)]']:
            with self.subTest(source=s),self.assertRaises(InputError): read(s)
        with self.assertRaises(InputError): read('D0Epfst('*85+'D0Eint(0)'+')'*85)

class RealBackend(unittest.TestCase):
    def setUp(self): self.b=LambdaBackend()
    def test_arithmetic_and_values(self):
        for s,e in [('D0Eop2("+", D0Eint(20), D0Eint(22))','D0Vint(arg1=42)'),
                    ('D0Elet("x", D0Eint(7), D0Evar("x"))','D0Vint(arg1=7)'),
                    ('D0Epsnd(D0Epair(D0Eint(1), D0Ebtf(True)))','D0Vbtf(arg1=True)'),
                    ('D0Eapp(D0Elam("x", D0Eop1("+1", D0Evar("x"))), D0Eint(2))','D0Vint(arg1=3)')]:
            with self.subTest(source=s):
                r=self.b.interpret(s,7); self.assertEqual((r.outcome,r.text,r.revision),('success',e,7))
    def test_factorial_fibonacci_base_cases(self):
        for name,n,e in [('factorial',5,120),('factorial',0,1),('factorial',1,1),
                         ('fibonacci',8,21),('fibonacci',0,0),('fibonacci',1,1)]:
            s=(SAMPLES/f'{name}.lambda').read_text(); default=5 if name=='factorial' else 8
            s=s.rsplit(f'D0Eint({default}))',1)[0]+f'D0Eint({n}))'
            with self.subTest(name=name,n=n):
                r=self.b.interpret(s,1); self.assertEqual((r.outcome,r.text),('success',f'D0Vint(arg1={e})'))
    def test_error_classification(self):
        for s,e in [('D0Eint("bad")','input_error'),('D0Eop2("/", D0Eint(1), D0Eint(0))','runtime_error'),
                    ('D0Evar("x")','runtime_error'),
                    ('D0Epair(D0Eint(1), D0Epair(D0Evar("x"), D0Eint(2)))','runtime_error'),
                    ('D0Eapp(D0Eint(1), D0Eint(2))','runtime_error'),
                    ((SAMPLES/'nonterminating.lambda').read_text(),'runtime_error')]:
            with self.subTest(source=s): self.assertEqual(self.b.interpret(s,1).outcome,e)
    def test_timeout_and_retry(self):
        b=LambdaBackend(timeout=0)
        self.assertEqual(b.interpret('D0Eint(1)',1).outcome,'backend_failure')
        b.timeout=2; self.assertEqual(b.interpret('D0Eint(1)',1).outcome,'success')
    def test_placeholders(self):
        for op in ['typecheck','compile']:
            r=getattr(self.b,op)('D0Eint(1)',2)
            self.assertEqual((r.operation,r.revision,r.outcome),(op,2,'not_implemented'))
        self.assertEqual(self.b.execute(Artifact(2,'future',b'')).outcome,'not_implemented')

class ModelTests(unittest.TestCase):
    def test_manual_apply_discard_revisions(self):
        m=Model(); m.manual(); m.edit('D0Eint(1)'); m.apply(); self.assertEqual(m.revision,1)
        m.results.append(Result('lint',1,'success','ok')); m.artifact=Artifact(1,'test',b'x')
        m.edit('D0Eint(2)')
        with self.assertRaises(StateError): m.begin('lint')
        with self.assertRaises(StateError): m.replace('D0Eint(3)','other')
        m.discard(); self.assertEqual(m.draft,m.source)
        m.replace('D0Eint(3)','uploaded'); self.assertEqual(m.revision,2)
        self.assertEqual(m.results,[]); self.assertIsNone(m.artifact)
    def test_rejected_changes_preserve_applied(self):
        m=Model(); m.replace('D0Eint(1)','original')
        for text in ['   ','x'*(MAX_BYTES+1),'é'*(MAX_BYTES//2+1)]:
            m.edit(text)
            with self.assertRaises(StateError): m.apply()
            self.assertEqual((m.source,m.name,m.revision),('D0Eint(1)','original',1))
            self.assertEqual(m.draft,text); m.discard()
    def test_busy_and_execute_guards(self):
        m=Model()
        with self.assertRaises(StateError): m.begin('lint')
        m.replace('D0Eint(1)','source'); m.begin('interpret')
        for action in [lambda:m.edit('x'),m.discard,m.apply,m.manual,lambda:m.begin('lint')]:
            with self.assertRaises(StateError): action()
        m.finish(Result('interpret',1,'backend_failure','failure'))
        self.assertFalse(m.busy); self.assertEqual(m.source,'D0Eint(1)')
        with self.assertRaises(StateError): m.begin('execute')
        m.artifact=Artifact(0,'test',b'')
        with self.assertRaises(StateError): m.begin('execute')
        m.artifact=Artifact(1,'test',b''); m.begin('compile'); self.assertIsNone(m.artifact)

class FakeBackend:
    def __init__(self): self.calls=[]; self.fail=False; self.gate=None
    def response(self,op,s,r):
        self.calls.append((op,s,r))
        if self.gate: self.gate.wait(2)
        if self.fail: raise RuntimeError('Injected failure')
        return Result(op,r,'success' if op in ('lint','interpret') else 'not_implemented','test result')
    def lint(self,s,r): return self.response('lint',s,r)
    def interpret(self,s,r): return self.response('interpret',s,r)
    def typecheck(self,s,r): return self.response('typecheck',s,r)
    def compile(self,s,r): return self.response('compile',s,r)
    def execute(self,a): raise AssertionError('Execute must not be called')

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.b=FakeBackend(); self.c=Controller(backend=self.b)
        self.c.request('edit',{'text':'D0Eint(42)'}); self.c.request('apply',{})
    def test_dispatch_placeholders(self):
        for op in ['lint','interpret','typecheck','compile']:
            self.c.request('action',{'operation':op}); r=wait(self.c)
            self.assertEqual(self.b.calls[-1],(op,'D0Eint(42)',1))
            self.assertEqual(r['outcome'],'success' if op in ('lint','interpret') else 'not_implemented')
        self.c.request('action',{'operation':'execute'})
        self.assertFalse(self.c.state()['executable']); self.assertEqual(len(self.b.calls),4)
    def test_busy_failure_retry(self):
        self.b.gate=threading.Event(); self.b.fail=True
        self.c.request('action',{'operation':'interpret'}); self.assertTrue(self.c.state()['busy'])
        self.c.request('edit',{'text':'bad'}); self.c.request('load',{'choice':'factorial'})
        self.assertEqual(self.c.state()['source'],'D0Eint(42)')
        self.b.gate.set(); self.assertEqual(wait(self.c)['outcome'],'backend_failure')
        self.b.gate=None; self.b.fail=False
        self.c.request('action',{'operation':'interpret'}); self.assertEqual(wait(self.c)['outcome'],'success')
    def test_upload_rejection_replacement(self):
        def upload(raw): return self.c.request('upload',{'bytes':base64.b64encode(raw).decode(),'name':'file.lambda'})
        s=upload(b'\xff'); self.assertIn('UTF-8',s['notice']); self.assertEqual(s['revision'],1)
        s=upload(b' '); self.assertEqual(s['draft'],' '); self.assertEqual(s['source'],'D0Eint(42)')
        self.c.request('discard',{}); s=upload(b'x'*(MAX_BYTES+1)); self.assertEqual(len(s['draft']),MAX_BYTES+1)
        self.c.request('discard',{}); s=upload(b'D0Eint(9)'); self.assertEqual(s['revision'],2)
        s=self.c.request('load',{'choice':'factorial'}); self.assertEqual(s['revision'],3)
        self.c.request('manual',{}); self.assertEqual(self.c.state()['draft'],''); self.assertTrue(self.c.state()['dirty'])
    def test_contract_violation_recovers(self):
        self.b.lint=lambda s,r: Result('wrong',999,'success','bad')
        self.c.request('action',{'operation':'lint'}); self.assertEqual(wait(self.c)['outcome'],'backend_failure')

class HttpTests(unittest.TestCase):
    def test_loopback_routes_literal_source(self):
        import urllib.request,json
        server=make_server(0,Controller(backend=FakeBackend()))
        t=threading.Thread(target=server.serve_forever,daemon=True); t.start()
        try:
            self.assertEqual(server.server_address[0],'127.0.0.1')
            url=f'http://127.0.0.1:{server.server_port}'
            html=urllib.request.urlopen(url).read().decode(); self.assertLess(html.index('>Lint<'),html.index('>Interpret<'))
            data=json.dumps({'command':'edit','data':{'text':'D0Evar("<b>x</b>")'}}).encode()
            req=urllib.request.Request(url+'/api/command',data=data,headers={'Content-Type':'application/json'})
            self.assertEqual(json.load(urllib.request.urlopen(req))['draft'],'D0Evar("<b>x</b>")')
        finally: server.shutdown(); server.server_close(); t.join()

if __name__=='__main__': unittest.main()
