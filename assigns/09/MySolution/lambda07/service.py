"""Parameter validation, supplied LAMBDA3 adapter, and terminable interpretation."""
import importlib
import json
import logging
import multiprocessing as mp
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory
from errors import RpcError

MAX_SOURCE_BYTES = 16_384
INTERPRET_SECONDS = 2.0
LOGGER = logging.getLogger(__name__)

def load_backend():
    """Use the provided implementation and its actual support files."""
    local = Path(__file__).resolve().parent / "LAMBDA3"
    original = local.parent.parent / "LAMBDA3"
    for directory in (original / "mylib", original, local / "mylib", local):
        text = str(directory)
        if text not in sys.path:
            sys.path.insert(0, text)
    return importlib.import_module("lambda3")

def parse_checked(backend, source):
    try:
        expression, typ = backend.d0exp_parse_and_typecheck(source)
        return expression, backend.format_type(typ)
    except backend.LambdaSyntaxError as exc:
        # Use the parser's short message, never SyntaxError's filename rendering.
        data = {"kind": "syntax", "detail": exc.msg}
        if exc.lineno is not None:
            data["line"] = exc.lineno
        if exc.offset is not None:
            data["column"] = exc.offset
        raise RpcError(-32010, "LAMBDA syntax error", data) from None
    except backend.TypeCheckError as exc:
        raise RpcError(-32011, "LAMBDA type error",
                       {"kind": "type", "detail": str(exc)}) from None

def interpretation_worker(result_path, source):
    """Spawn entry point: ASTs and closures remain inside the child process."""
    try:
        backend = load_backend()
        expression, typ = parse_checked(backend, source)
        value = backend.d0exp_evaluate(expression)
        outcome = ("result", {"type": typ, "value": backend.d0val_format(value)})
    except RpcError as exc:
        outcome = ("error", (exc.code, exc.message, exc.data))
    except Exception:
        LOGGER.exception("LAMBDA interpretation failed")
        outcome = ("error", (-32603, "Internal error", None))
    # A file avoids blocking on a full IPC pipe for large formatted values
    with open(result_path, "w", encoding="utf-8") as destination:
        json.dump(outcome, destination)

def run_interpretation(source, seconds=INTERPRET_SECONDS, worker=interpretation_worker):
    """Bound startup, parsing, evaluation, formatting and result writing."""
    context = mp.get_context("spawn")
    with TemporaryDirectory(prefix="lambda-rpc-") as directory:
        result_path = str(Path(directory) / "result.json")
        process = context.Process(target=worker, args=(result_path, source), daemon=True)
        deadline = time.monotonic() + seconds
        try:
            process.start()
            process.join(timeout=max(0, deadline - time.monotonic()))
            if process.is_alive() or time.monotonic() > deadline:
                raise RpcError(-32012, "Execution timeout",
                               {"kind": "timeout", "limit_seconds": seconds})
            if process.exitcode != 0 or not Path(result_path).is_file():
                LOGGER.error("Interpretation worker exited without a result")
                raise RpcError(-32603, "Internal error")
            with open(result_path, encoding="utf-8") as result_file:
                kind, payload = json.load(result_file)
            if kind == "error":
                raise RpcError(*payload)
            return payload
        finally:
            # No child may continue computing after a response/deadline expiry.
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=0.2)
                if process.is_alive():
                    process.kill()
                    process.join()
                process.close()

class LambdaService:
    def __init__(self, seconds=INTERPRET_SECONDS):
        self.seconds = seconds

    def call(self, method, params):
        names = {"service.health", "lambda.typecheck", "lambda.interpret", "lambda.compile"}
        if method not in names:
            raise RpcError(-32601, "Method not found")
        expected = ({"source", "target"} if method == "lambda.compile" else
                    set() if method == "service.health" else {"source"})
        if not isinstance(params, dict) or set(params) != expected:
            raise RpcError(-32602, "Invalid params", {"expected_keys": sorted(expected)})
        if method == "service.health":
            return {"status": "ok", "version": "1.0"}
        source = params["source"]
        if not isinstance(source, str) or not source.strip():
            raise RpcError(-32602, "Invalid params", {"field": "source", "reason": "nonempty string required"})
        try:
            size = len(source.encode("utf-8"))
        except UnicodeEncodeError:
            raise RpcError(-32602, "Invalid params", {"field": "source", "reason": "invalid Unicode"}) from None
        if size > MAX_SOURCE_BYTES:
            raise RpcError(-32602, "Invalid params", {"field": "source", "max_bytes": MAX_SOURCE_BYTES})
        if method == "lambda.compile" and params["target"] not in ("python", "javascript"):
            raise RpcError(-32602, "Invalid params", {"field": "target", "allowed": ["python", "javascript"]})
        if method == "lambda.interpret":
            return run_interpretation(source, self.seconds)
        backend = load_backend()
        expression, typ = parse_checked(backend, source)
        if method == "lambda.typecheck":
            return {"type": typ}
        target = params["target"]
        compiler = backend.d0exp_compile if target == "python" else backend.d0exp_compile_js
        return {"target": target, "code": compiler(expression)}
