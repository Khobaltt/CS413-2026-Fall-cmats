# LAMBDA MVC Workbench

A local Flask application with real free-variable checking and interpretation,
using the supplied `lambda1.py` unchanged. Type-check and Compile are explicit
placeholders; Execute is reserved for generated code and remains disabled.

## Setup, run, and tests

Requires Python **3.12 or later**. Verified with Python 3.12.14, Flask 3.1.2,
Werkzeug 3.1.9, Node 24.19.0, Playwright 1.62.1, and headless Chromium 133.0.6943.0.
All Python packages are pinned in `requirements.txt`. Unit tests use `unittest`.

From the extracted submission root:

```bash
cd assigns/04/MySolution
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Open **http://127.0.0.1:8000/**. Stop with Ctrl+C. Choose another local port with
`.venv/bin/python app.py --port 8001`. The server always binds `127.0.0.1`; debug
mode and the automatic reloader are not enabled. On Windows use
`py -3.12 -m venv .venv`, then `.venv\Scripts\python.exe` instead of
`.venv/bin/python` in the commands above and below.

Run automated Python checks from `MySolution`:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The optional browser smoke test needs Node.js 20+ and Playwright/Chromium. With
the server already running in a separate terminal:

```bash
npm install
npx playwright install chromium
npm run test:browser
```

The test writes `browser-results.json` and `browser-smoke.png` in the current
directory. To use an existing Chromium binary:

```bash
CHROMIUM_PATH=/absolute/path/to/chromium npm run test:browser
```

`BASE_URL` can select another loopback port. Browser dependencies are optional
and are not required for running the application or Python tests. Do not submit
`.venv`, `node_modules`, or caches. Existing browser results and a screenshot
from the completed smoke test are included. See `TESTING.md` for traceability.

## Demonstration

1. Select **Factorial (canned)** in Load source, then click **Load source**.
   The editable expression computes factorial(5). Click **Lint**, then
   **Interpret**: no free variables, followed by `D0Vint(arg1=120)`.
2. Select **Fibonacci (canned)** and load it. The revision increases and results
   clear. Interpret yields `D0Vint(arg1=21)` for Fibonacci(8).
3. Select **Manual input**, load it, and type `D0Evar("x")` into the blank editor.
   Click **Apply changes**, then **Lint**. It reports `language_error` and
   `Undeclared variables: x`. Edit to `D0Eint(42)`, Apply, and Lint again: no free
   variables. Interpret returns `D0Vint(arg1=42)`.
4. Apply `D0Eop2("/", D0Eint(1), D0Eint(0))`. Lint passes because the expression
   is closed; Interpret reports `runtime_error` with `ZeroDivisionError`.
   Closedness does not establish that evaluation is safe or well-typed.
5. Click **Type-check** and **Compile**. Each result has outcome
   `not_implemented` and says the operation is not yet implemented. **Execute**
   stays disabled because it needs compiler-generated code, which does not exist.
6. Edit any applied expression. Tool actions and source replacement become
   unavailable until **Apply changes** or **Discard changes**. Applying blank
   or oversized input keeps the rejected draft and previous applied revision;
   Discard restores the applied source. Choose File accepts local UTF-8 text
   through its labeled file input. It never changes the original local file.

For timeout recovery, load Fibonacci, edit only its final argument to
`D0Eint(35)`, Apply, and Interpret. On the verified machine this exceeded the
2-second deadline, produced `backend_failure`, and released the controls.
Apply a small arithmetic expression to retry successfully.

## Supported input format

Input is **one constructor expression**, not a script. Python comments,
multiline nested calls, string/integer/Boolean literals, and signed integer
literals are accepted. Imports are unnecessary. Only positional arguments are
supported; there are no keywords, attribute accesses, arbitrary calls,
comprehensions, arithmetic Python expressions, `eval`, or `exec`.

| Constructor | Valid positional argument types |
| --- | --- |
| `D0E000()` | No arguments; explicit unsupported/error expression |
| `D0Eint(n)` | Integer, excluding Boolean |
| `D0Ebtf(b)` | Boolean |
| `D0Evar(name)` | String |
| `D0Eop1(op, expression)` | String, expression |
| `D0Eop2(op, left, right)` | String, expression, expression |
| `D0Elam(parameter, body)` | String, expression |
| `D0Efix(name, parameter, body)` | String, string, expression |
| `D0Eapp(function, argument)` | Expression, expression |
| `D0Eif0(condition, then, else)` | Three expressions; evaluated condition must be Boolean |
| `D0Elet(name, initializer, body)` | String, expression, expression |
| `D0Epair(left, right)` | Expression, expression |
| `D0Epfst(pair)`, `D0Epsnd(pair)` | Expression |

The supplied interpreter supports unary `+1`/`-1`, integer `+`, `-`, `*`, `/`
(floor division), and `<`, `>`, `<=`, `>=`, `==`, `!=`. An unsupported operation
is a runtime error. A nonrecursive let does not bind its name in its initializer.
Unused parameters/bindings are permitted. Factorial examples treat n <= 1 as 1;
Fibonacci examples treat n <= 1 as n and are intended for nonnegative integers.

## Bounds and limitations

Applied source is limited to **32,768 UTF-8 bytes**. Reader traversal allows at
most 4,000 AST nodes and nesting depth 80. The HTTP envelope is limited to 1 MiB;
the browser rejects uploaded files above 500,000 bytes before transmission.
Oversized textual uploads below that envelope remain editable rejected drafts;
files too large to transmit remain available in the original local file.
Invalid UTF-8 bytes cannot become a textual draft, so the prior editor is kept.

Lint and Interpret run in spawned worker processes with a **2-second deadline**,
including startup. The worker is terminated on timeout; cleanup can add up to
0.5 seconds before a forced kill. Python recursion errors are runtime failures,
not successful results. Text output is capped at 16,000 characters. This is a
local educational application, not a resource-isolated public code service.
There is one shared in-memory model, intended for one user and one active tab;
server restart loses all state. No persistence, accounts, concrete-syntax parser,
type checker, compiler, or generated-code runner is included.

## Reflection

MVC helped most with making source state explicit. The model distinguishes the
applied program from the editable draft, so a failed Apply does not destroy the
program that previously worked. Revision numbers also provide a concrete way to
explain which source produced each result. These rules are tested directly,
without starting Flask or opening a browser, which made mistakes in state
transitions easier to find.

The controller provides one place to coordinate language operations. It captures
the current revision, selects the correct backend method, and records completion.
Substituting a backend that raises an exception allowed failure and retry tests
without changing rendering code. The view consequently only needs to display
state and forward interactions. It has no knowledge of lexical scope, closures,
or the interpreter's environment representation.

The hardest separation was managing unapplied edits and asynchronous work.
Browser controls need immediate feedback, but disabled buttons cannot be the
authority for application rules. The model therefore enforces the same guards,
while the view reflects them. Background work also requires careful coordination:
the busy flag is set before dispatch, and every adapter exception must become a
result so the application can recover.

A future compiler would benefit from these boundaries. Its adapter could return
a revision-tagged artifact, while the controller installs it only after successful
compilation. Execute could then consume that artifact through a separate bounded
runner. The existing model invalidation rules would prevent old generated code
from running after source changes. This extension would require a richer backend
response contract, but would leave the editor and result rendering largely intact.

## Files and review

`ARCHITECTURE.md` explains actual dependencies and the adapter contract.
`SOLUTION_EXPLANATIONS.md` gives a few sentences for every task, F1–F10, testing
requirement, and submission requirement. `AI-TRANSCRIPT.md` discloses AI use.
`lambda1.py` is the unchanged supplied file. `git-history.bundle` preserves
meaningful commits; recover them with `git clone git-history.bundle recovered`
from this directory. The extracted zip is also directly runnable.