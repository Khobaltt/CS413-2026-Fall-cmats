"""JSON-RPC 2.0 envelopes, independent of HTTP and LAMBDA3."""

"""STEP 4: Strict IDs, envelopes, notifications, and safe errors."""
import math
from errors import RpcError

def valid_id(value):
    return (value is None or isinstance(value, str) or type(value) is int
            or (type(value) is float and math.isfinite(value)))

def error(code, message, request_id=None):
    return {'jsonrpc': '2.0', 'error': {'code': code, 'message': message}, 'id': request_id}

def dispatch(request, service):
    if (not isinstance(request, dict)
            or request.get('jsonrpc') != '2.0'
            or not isinstance(request.get('method'), str)
            or ('id' in request and not valid_id(request['id']))):
        return error(-32600, 'Invalid Request')
    notification = 'id' not in request
    request_id = request.get('id')
    try:
        result = service.call(request['method'], request.get('params', {}))
        response = {'jsonrpc': '2.0', 'result': result, 'id': request_id}
    except RpcError as exc:
        response = error(exc.code, exc.message, request_id)
    except Exception:
        response = error(-32603, 'Internal error', request_id)
    return None if notification else response
