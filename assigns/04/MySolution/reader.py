"""Walk Python's AST as data; never eval/exec uploaded input."""
import ast
import lambda1 as L

class InputError(ValueError):
    pass

SCHEMA = {
    'D0E000': (), 'D0Eint': (int,), 'D0Ebtf': (bool,), 'D0Evar': (str,),
    'D0Eop1': (str, L.D0E000), 'D0Eop2': (str, L.D0E000, L.D0E000),
    'D0Elam': (str, L.D0E000), 'D0Efix': (str, str, L.D0E000),
    'D0Eapp': (L.D0E000, L.D0E000), 'D0Eif0': (L.D0E000,)*3,
    'D0Elet': (str, L.D0E000, L.D0E000), 'D0Epair': (L.D0E000,)*2,
    'D0Epfst': (L.D0E000,), 'D0Epsnd': (L.D0E000,),
}

def read(source):
    try:
        tree = ast.parse(source.strip(), mode='eval')
        if sum(1 for _ in ast.walk(tree)) > 4000:
            raise InputError('Too many syntax nodes (limit 4000).')
        def visit(node, depth=0):
            if depth > 80:
                raise InputError('Constructor nesting exceeds 80.')
            if isinstance(node, ast.Constant) and type(node.value) in (int, bool, str):
                return node.value
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
                value = visit(node.operand, depth+1)
                if type(value) is int:
                    return -value if isinstance(node.op, ast.USub) else value
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id not in SCHEMA:
                raise InputError('Only listed LAMBDA constructors and literal arguments are allowed.')
            name = node.func.id
            schema = SCHEMA[name]
            if node.keywords or len(node.args) != len(schema):
                raise InputError(f'{name} expects {len(schema)} positional arguments; keywords are not supported.')
            values = [visit(n, depth+1) for n in node.args]
            for index, (value, kind) in enumerate(zip(values, schema), 1):
                ok = isinstance(value, kind) if kind is L.D0E000 else type(value) is kind
                if not ok:
                    raise InputError(f'{name} argument {index} must be {kind.__name__}.')
            return getattr(L, name)(*values)
        value = visit(tree.body)
        if not isinstance(value, L.D0E000):
            raise InputError('Top-level input must be a d0exp constructor.')
        return value
    except (SyntaxError, RecursionError, ValueError) as exc:
        if isinstance(exc, InputError):
            raise
        raise InputError(f'Invalid constructor expression: {exc}') from exc
