"""Bridge to the supplied, unmodified LAMBDA3 interpreter."""

"""Load and type-check only the fixed solver."""
import sys
from pathlib import Path
from functools import lru_cache

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'LAMBDA3'))
import lambda3 as L

@lru_cache(maxsize=1)
def program():
    expression = L.d0exp_parse((ROOT / 'queens.lam').read_text())
    L.d0exp_typecheck(expression)
    return L.d0exp_evaluate(expression)

def invoke(function, value):
    """Apply a runtime value through the public AST/evaluator interface."""
    env = L.ENVcns('fn', function, L.ENVcns('arg', value, L.ENVnil()))
    return L.d0exp_evaluate(L.d0exp_parse('fn(arg)'), env)

def open_stream(size):
    return invoke(program().arg1[0], L.D0Vint(size))