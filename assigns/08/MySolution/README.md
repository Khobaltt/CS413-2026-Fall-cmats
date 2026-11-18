<!-- Setup, operation, API examples, and limitations -->
# Animated N-Queens with CPS and lazy streams

A fixed, type-checked LAMBDA3 CPS program searches rows in order and columns
left to right. The browser consumes its lazy trace one event at a time.
Default board: 8×8; supported boards: 4–10. Exactly 92 solutions on 8×8.

## Files and dependencies

Use Python **3.12 or later**. The application and Python tests use only the
standard library; `requirements.txt` contains no pip dependencies. Node.js 18+
is needed only for the JavaScript tests. A current browser runs the interface.
The optional browser smoke test additionally needs Playwright and Chromium.

Keep the supplied structure:

```
assigns/08/
  Assign08.md
  LAMBDA3/                 # supplied, unchanged
    lambda3.py
    basics0.py
    mylib/
    mytest/
  MySolution/
    queens.lam            # real CPS search and lazy event stream
    solver.py             # type check, interpreter bridge, event conversion
    errors.py
    service.py            # cursors, limits, cleanup, locking
    dispatcher.py         # JSON-RPC envelopes
    app.py                # HTTP and static assets
    requirements.txt
    static/               # index.html, style.css, client.mjs
    tests/                # Python, JS, optional browser smoke test
    DESIGN.md
    TESTING.md
    AI-TRANSCRIPT.md
    README.md
```

Only `MySolution/` is your submission. Do not submit virtual environments,
`__pycache__`, installed Node dependencies, browser downloads, or generated state.
See `PLAN.md` for the numbered checklist and `COMMIT-MESSAGES.md` for commits.

## Run

From `assigns/08` (the extracted `08` directory):

```bash
python3 --version
python3 MySolution/app.py
```

Open **http://127.0.0.1:8000/**. Stop with Ctrl+C. To change the port:

```bash
python3 MySolution/app.py --port 9000
```

Keep the page on this same origin so relative `/rpc` requests work. Do not open
`index.html` directly as a file. No external service, API key, account, or network
connection is needed during ordinary operation.

## Controls

- **Start:** close the previous search if present, open a new stream, clear count.
  It does not request the first event. Also restarts after completion/errors.
- **Step:** consume and render exactly one event.
- **Play/Pause:** fetch and render one event per interval; pause stops future
  requests. A request already in flight may finish and render once.
- **Next solution:** consume incrementally until the next solution or exhaustion;
  use Pause to interrupt. The speed delay also applies here.
- **Reset:** pause, wait for in-flight consumption, close the stream, clear display.
- **Board size:** choose 4–10 before starting, or after Reset; default is 8.
- **Delay:** 0–1000 milliseconds between events. HTTP and rendering add overhead.

Try is gold; place is green; reject is red with ×; backtrack is purple with ↶;
solution uses a gold board border. The trace also names each event, so color is
not the only signal. Solutions increment the count; only `done` marks completion.
The log keeps the most recent 30 events. Playback never preloads the full trace.
An 8×8 trace has 33,589 events, so use 4×4 or delay 0 for a quicker demonstration.

## Tests

Run from `assigns/08`:

```bash
python3 -m unittest discover -s MySolution/tests -v
node --test MySolution/tests/client.test.mjs
```

The Python suite includes a real local HTTP server on an automatically selected
port and completes the full 8×8 run. The JS suite tests playback and DOM wiring
with deterministic transport/DOM doubles. See `TESTING.md` for requirement
mapping, observed results, and the manual browser checklist.

Optional real browser test: install Playwright in `MySolution` (development only),
then install its browser. Keep the app running in another terminal.

```bash
cd MySolution
npm install --no-save --package-lock=false playwright
npx playwright install chromium
cd ..
node MySolution/tests/browser-smoke.cjs
```

For a different local port, set `QUEENS_URL=http://127.0.0.1:9000` before the node
command. `CHROMIUM_PATH` can specify an existing Chromium executable. The
smoke test checks actual browser controls, error recovery, and mobile width.
These optional downloads are not required for the app or the core tests.

## JSON-RPC examples

POST to `/rpc` with `Content-Type: application/json`. Every example below is a
separate JSON request. Calls use HTTP 200; valid notifications omit `id` and
receive HTTP 204 with no body. No batch support.

```bash
curl -sS http://127.0.0.1:8000/rpc \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"service.health","params":{},"id":1}'
```

```json
{"jsonrpc":"2.0","method":"queens.open","params":{"size":8},"id":2}
```

Copy the returned `stream_id` into subsequent calls:

```json
{"jsonrpc":"2.0","method":"queens.next","params":{"stream_id":"UUID","limit":1},"id":3}
{"jsonrpc":"2.0","method":"queens.close","params":{"stream_id":"UUID"},"id":4}
```

`queens.next` accepts integer limits 1–32 and returns `events` and `done`.
The response containing the final `done` event sets `done: true`. Later calls
return `events: [], done: true` until close, expiration, or tombstone eviction.
Events contain `event`, `board` in row order, and `row`/`column` for candidate
and backtrack events. Solution contains its full board; done only its event name.
See `DESIGN.md` for complete schemas and example responses for all methods.

## Limits, errors, and cleanup

Streams expire after 300 seconds of inactivity. Cleanup runs every server-loop
iteration (one second) and before each RPC method. UUIDs are process-local and
invalid after restart. Maximum active streams: 128. Completed streams release
their live closures immediately; at most 1024 small completion tombstones remain.
They expire after 300 idle seconds and the oldest is evicted at capacity.
Closing an active or completed stream succeeds; closing it again is an error.

| Code | Meaning |
|---|---|
| -32700 | Parse error, including invalid UTF-8 or non-JSON constants |
| -32600 | Invalid request envelope, ID, or unsupported batch |
| -32601 | Method not found |
| -32602 | Wrong parameter shape, type, size, or limit |
| -32603 | Internal error; details are hidden |
| -32001 | Unknown, closed, expired, or evicted stream ID |
| -32002 | Active-stream capacity reached |

Parameter objects require exactly the documented keys. Booleans are not accepted
as integers. Request bodies are limited to 64 KiB. Non-JSON content types use
HTTP 415 and oversized bodies use HTTP 413. No interpreter values, closures,
filesystem paths, or tracebacks are sent to the browser.

## Reuse and limitations

The supplied `LAMBDA3/lambda3.py`, `basics0.py`, libraries, and examples remain
unchanged. `queens.lam` uses the conflict arithmetic and lazy primitive syntax
shown in `mytest/eight_queens_stream.lam`. Its CPS control flow and event model
are newly implemented; it does not wrap that example's direct-style search.
No Assignment 7 files were provided or reused. The small RPC subset is new.

The server is for local use, binds to 127.0.0.1, and has no authentication,
persistence, public deployment, or arbitrary-code RPC. A single lock serializes
stream operations. The supplied evaluator is recursive; LAMBDA tail-position
calls do not imply a general Python trampoline. Frequent lazy event boundaries
and the size limit keep each force bounded for the required boards.
