# LAMBDA3 JSON-RPC contract, API version 1.0

Transport: `POST http://127.0.0.1:5000/rpc`, `Content-Type: application/json`.
JSON is UTF-8. Names are case-sensitive. Extra envelope members are ignored.
All methods require an explicit object `params` with exactly the keys below;
missing params, arrays, extra keys, wrong types, and invalid values produce
-32602. Unknown methods produce -32601, including when their params are bad.

| Method | Params | Result |
| --- | --- | --- |
| `service.health` | `{}` | `{"status":"ok","version":"1.0"}` |
| `lambda.typecheck` | `{"source":"..."}` | `{"type":"sint"}` |
| `lambda.interpret` | `{"source":"..."}` | `{"type":"sint","value":"42"}` |
| `lambda.compile` | `{"source":"...","target":"python"}` | `{"target":"python","code":"..."}` |
| `lambda.compile` | `{"source":"...","target":"javascript"}` | `{"target":"javascript","code":"..."}` |

Source must be nonblank, valid Unicode and at most **16,384 UTF-8 bytes**.
Interpretation has a **2.0-second wall-clock deadline**, including worker
startup, parsing, type-checking, evaluation, formatting, and result-file writing.
The worker is terminated (and killed if necessary), then reaped. Cleanup can
add a small delay after the deadline. A timeout does not prove nontermination;
recursive programs may instead hit Python's recursion limit, reported as an
internal error. Typecheck and compile are synchronous and have no separate
execution deadline. The HTTP body limit is **1,048,576 bytes**.

All source operations call `d0exp_parse_and_typecheck`. Types use `format_type`;
interpretation uses `d0exp_evaluate` and `d0val_format`; compilation uses
`d0exp_compile` / `d0exp_compile_js`. Generated code is returned unchanged and
is never executed. Function values are `<lam>` / `<fix>`, not environments.
Health reports the RPC API's status/version; it is not a backend readiness test.

## Envelopes and HTTP status

Requests carry `jsonrpc: "2.0"`, a string `method`, object `params`, and an
optional `id`. IDs may be strings, finite JSON numbers, or null, never booleans,
arrays, or objects. Explicit null is a call ID; absent ID is a notification.
Replies preserve a usable ID and have exactly one of `result` and `error`.
Invalid envelopes preserve a usable supplied ID; otherwise the ID is null.
Invalid requests without IDs receive an error; they are not notifications.

Valid notifications are processed but have no response, even for unknown
methods, bad method parameters, or application failures. A nonempty batch
returns an array with each call's response and each invalid member's error,
excluding notifications. Clients correlate by ID, not array position; IDs
need not be unique. Empty batches return one -32600 object, not an array.
A notification or notification-only batch produces HTTP **204**, empty body.

All JSON-RPC replies, including malformed JSON and RPC errors, use HTTP **200**
and `application/json`. HTTP **415** means unsupported Content-Type; HTTP
**413** means body too large; HTTP **405** means the route's verb is wrong;
HTTP **404** means no such endpoint. These are transport failures, not RPC
errors; framework-generated transport bodies are not JSON-RPC envelopes.
`application/json; charset=utf-8` is accepted; `application/*+json` is not.
NaN, Infinity, invalid UTF-8 and malformed JSON produce -32700.

## Error mapping

| Code | Message | Data |
| --- | --- | --- |
| -32700 | Parse error | omitted |
| -32600 | Invalid Request | omitted |
| -32601 | Method not found | omitted |
| -32602 | Invalid params | expected keys, or field/reason, max_bytes, or allowed targets |
| -32603 | Internal error | omitted; exception logged server-side |
| -32010 | LAMBDA syntax error | kind=syntax, detail; line/column when available |
| -32011 | LAMBDA type error | kind=type, detail |
| -32012 | Execution timeout | kind=timeout, limit_seconds |

Only known language diagnostics are exposed. Unexpected errors, including
runtime failures, disclose no Python exception strings, tracebacks or paths.
Source syntax failure is -32010, never a JSON decoding error (-32700).

## Complete examples

Health request and response:
```json
{
    "jsonrpc":"2.0",
    "id":"health",
    "method":"service.health",
    "params":{}
}
```
```json
{
    "jsonrpc":"2.0",
    "id":"health",
    "result":
    {
        "status":"ok",
        "version":"1.0"
    }
}
```
Typecheck request and response:
```json
{
    "jsonrpc":"2.0",
    "id":1,
    "method":"lambda.typecheck",
    "params":
    {
        "source":"6 * 7"
    }
}
```
```json
{
    "jsonrpc":"2.0",
    "id":1,
    "result":
    {
        "type":"sint"
    }
}
```
Factorial request and response:
```json
{
    "jsonrpc":"2.0",
    "id":2,
    "method":"lambda.interpret",
    "params":
    {
        "source":"let fact : sint -> sint = fix fact(n: sint): sint => if n <= 1 then 1 else n * fact(n - 1) in fact(6) end"
    }
}
```
```json
{
    "jsonrpc":"2.0",
    "id":2,
    "result":
    {
        "type":"sint",
        "value":"720"
    }
}
```
Compilation request:
```json
{
    "jsonrpc":"2.0",
    "id":3,
    "method":"lambda.compile",
    "params":
    {
        "source":"42",
        "target":"python"
    }
}
```
The complete, exact response for this request (including the supplied
compiler's full runtime) is in `examples/compile-response.json`. The matching
request is `examples/compile-request.json`. JavaScript uses target
`"javascript"` and the same envelope. These examples are produced through
the HTTP test client, not by executing generated code.

Syntax error:
```json
{
    "jsonrpc":"2.0",
    "id":4,
    "method":"lambda.typecheck",
    "params":
    {
        "source":"@"
    }
}
```
```json
{
    "jsonrpc":"2.0",
    "id":4,
    "error":
    {
        "code":-32010,
        "message":"LAMBDA syntax error",
        "data":
        {
            "kind":"syntax",
            "detail":"Unexpected character '@'",
            "line":1,
            "column":1
        }
    }
}
```
Unbound-variable/type error:
```json
{
    "jsonrpc":"2.0",
    "id":5,
    "method":"lambda.typecheck",
    "params":
    {
        "source":"missing"
    }
}
```
```json
{
    "jsonrpc":"2.0",
    "id":5,
    "error":
    {
        "code":-32011,
        "message":"LAMBDA type error",
        "data":
        {
            "kind":"type",
            "detail":"unbound variable 'missing'"
        }
    }
}
```
Mixed batch:
```json
[
    {
        "jsonrpc":"2.0",
        "id":"a",
        "method":"service.health",
        "params":{}
    },
    {
        "jsonrpc":"2.0",
        "method":"service.health",
        "params":{}
    },
    {
        "jsonrpc":"2.0",
        "id":7,
        "method":"lambda.typecheck",
        "params":
        {
            "source":"true"
        }
    },
    17
]
```
```json
[
    {
        "jsonrpc":"2.0",
        "id":"a",
        "result":
        {
            "status":"ok",
            "version":"1.0"
        }
    },
    {
        "jsonrpc":"2.0",
        "id":7,
        "result":
        {
            "type":"bool"
        }
    },
    {
        "jsonrpc":"2.0",
        "id":null,
        "error":
        {
            "code":-32600,
            "message":"Invalid Request"
        }
    }
]
```
Notification-only batch (HTTP 204 with **zero response bytes**):
```json
[
    {
        "jsonrpc":"2.0",
        "method":"service.health",
        "params":{}
    }
]
```

## Schema and references

`rpc-schema.json` is a JSON Schema Draft 2020-12 document. Validate a request
against `#/$defs/requestPayload` and a response against
`#/$defs/responsePayload`. The request schema describes valid envelopes;
method-specific exact keys and UTF-8 byte limits are also enforced by the
service. No response schema applies to an empty HTTP 204 body.

- JSON-RPC specification: https://www.jsonrpc.org/specification
- Flask test client: https://flask.palletsprojects.com/en/stable/testing/
