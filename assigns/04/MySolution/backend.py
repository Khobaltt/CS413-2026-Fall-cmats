"""Replaceable backend. Real operations run in killable spawned processes."""
import multiprocessing as mp
from typing import Protocol
import lambda1 as L
from reader import read, InputError
from model import Result, Artifact

class Backend(Protocol):
    def lint(self, source: str, revision: int) -> Result: ...
    def interpret(self, source: str, revision: int) -> Result: ...
    def typecheck(self, source: str, revision: int) -> Result: ...
    def compile(self, source: str, revision: int) -> Result: ...
    def execute(self, artifact: Artifact) -> Result: ...

def has_error(value):
    return type(value) is L.D0V000 or (isinstance(value, L.D0Vpair) and
            (has_error(value.arg1) or has_error(value.arg2)))

def compute(operation, source):
    try:
        expression = read(source)
    except InputError as exc:
        return 'input_error', str(exc)
    try:
        if operation == 'lint':
            free = L.d0exp_fvset(expression)
            return ('language_error', 'Undeclared variables: ' + ', '.join(sorted(free))) if free else ('success', 'No free variables were found.')
        value = L.d0exp_evaluate(expression, L.ENVnil())
        if has_error(value):
            return 'runtime_error', f'Evaluation returned an error sentinel: {value}'
        return 'success', str(value)
    except (TypeError, ZeroDivisionError, RecursionError, OverflowError, ValueError) as exc:
        return 'language_error' if operation == 'lint' else 'runtime_error', f'{type(exc).__name__}: {exc}'

def worker(conn, operation, source):
    try:
        conn.send(compute(operation, source))
    except Exception as exc:
        conn.send(('backend_failure', f'{type(exc).__name__}: {exc}'))
    finally:
        conn.close()

class LambdaBackend:
    def __init__(self, timeout=2.0):
        self.timeout = timeout

    def run(self, operation, source, revision):
        ctx = mp.get_context('spawn')
        parent, child = ctx.Pipe(duplex=False)
        process = ctx.Process(target=worker, args=(child, operation, source))
        try:
            process.start()
            child.close()
            if not parent.poll(self.timeout):
                return Result(operation, revision, 'backend_failure', f'Operation timed out after {self.timeout:g} seconds.')
            outcome, message = parent.recv()
            return Result(operation, revision, outcome, message[:16000])
        except (EOFError, OSError) as exc:
            return Result(operation, revision, 'backend_failure', f'Worker failed: {exc}')
        finally:
            if process.pid:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=0.5)
                if process.is_alive():
                    process.kill()
                    process.join()
            parent.close()
            child.close()

    def lint(self, source, revision):
        return self.run('lint', source, revision)
    def interpret(self, source, revision):
        return self.run('interpret', source, revision)
    def typecheck(self, source, revision):
        return Result('typecheck', revision, 'not_implemented', 'Type checking is not yet implemented.')
    def compile(self, source, revision):
        return Result('compile', revision, 'not_implemented', 'Compilation is not yet implemented.')
    def execute(self, artifact):
        return Result('execute', artifact.revision, 'not_implemented', 'Generated-code execution is not yet implemented.')
