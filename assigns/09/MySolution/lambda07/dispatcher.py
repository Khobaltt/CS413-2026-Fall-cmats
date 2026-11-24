"""JSON-RPC envelopes; deliberately independent of Flask and language internals."""
import logging
import math
from errors import RpcError
LOGGER = logging.getLogger(__name__)

def usable_id(value):
    return (value is None or isinstance(value, str) or type(value) is int
            or (type(value) is float and math.isfinite(value)))

def dispatch_one(item, service):
    if not isinstance(item, dict):
        return RpcError(-32600, "Invalid Request").response(None)
    request_id = item.get("id")
    valid_id = usable_id(request_id)
    if item.get("jsonrpc") != "2.0" or not isinstance(item.get("method"), str) or not valid_id:
        return RpcError(-32600, "Invalid Request").response(None)
    notification = "id" not in item
    try:
        # Missing params is a method-level error, including for notifications
        result = service.call(item["method"], item.get("params"))
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}
    except RpcError as exc:
        response = exc.response(request_id)
    except Exception:
        LOGGER.exception("Unexpected RPC backend failure")
        response = RpcError(-32603, "Internal error").response(request_id)
    return None if notification else response

def dispatch(payload, service):
    if not isinstance(payload, list):
        return dispatch_one(payload, service)
    if not payload:
        return RpcError(-32600, "Invalid Request").response(None)
    responses = []
    for item in payload:
        response = dispatch_one(item, service)
        if response is not None:
            responses.append(response)
    return responses or None
