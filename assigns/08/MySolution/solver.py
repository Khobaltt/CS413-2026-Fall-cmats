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

"""Force precisely one cell and translate its event"""
def force(stream):
    env = L.ENVcns('stream', stream, L.ENVnil())
    return L.d0exp_evaluate(L.d0exp_parse('lazy_eval(stream)'), env)

def event_json(value):
    tag, row, column, board = value.arg1
    names = ('try', 'place', 'reject', 'backtrack', 'solution', 'done')
    result = {'event': names[tag.arg1]}
    if tag.arg1 == 5:
        return result
    columns, items = [], board.arg1
    while isinstance(items, L.fnlist_cons):
        columns.append(items.arg1.arg1)
        items = items.arg2
    result['board'] = columns[::-1]
    if tag.arg1 < 4:
        result.update(row=row.arg1, column=column.arg1)
    return result