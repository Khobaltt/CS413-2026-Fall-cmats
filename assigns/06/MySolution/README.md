# Extended Lambda Calculus Compiler

This project compiles extended lambda-calculus source expressions into pure lambda calculus. The generated target AST contains only `Var`, `Lam`, and `App`. Numbers, booleans, arithmetic, comparisons, pairs, conditionals, and recursion are implemented using expanded Church encodings.

The pipeline is:

```text
Source AST → compile_expr → Target AST → evaluate → observe → Python result
```

The shared `evaluate` entry point also evaluates source expressions independently, allowing the demonstrations to compare the source answer, decoded target answer, and an explicit expected answer.

## Requirements and setup

- Python 3.12 or later
- Python standard library only; no packages need to be installed
- Place the project files under `assigns/06/MySolution/`
- Keep the supplied `lambda1_vp.py` unchanged and include the reused `visitors.py` alongside the implementation

Run all commands below from `assigns/06/`. The project uses sibling imports; the documented script and discovery commands make `MySolution` available for those imports.

## Files

| File | Responsibility |
|---|---|
| `lambda1_vp.py` | Supplied source AST, visitor interface, environments, and value classes |
| `visitors.py` | Reused source visitors, including `PrettyPrintVisitor` and `FreshNames` |
| `target.py` | Immutable target nodes, pure-term validation, and printing |
| `scope.py` | Free variables, all names, and capture-avoiding substitution |
| `church.py` | Closed Church builders for data and operations |
| `compiler.py` | Compilation visitor, delayed branches, and expanded call-by-value `Z` |
| `evaluator.py` | Shared source/target evaluation entry point |
| `observers.py` | Bounded natural, boolean, and nested-pair observation |
| `examples.py` | Fourteen demonstrations and explicit expected answers |
| `demo.py` | Command-line pipeline and reports |
| `test_*.py` | Automated `unittest` suite |
| `DESIGN.md` | Translation rules, implementation decisions, and correctness discussion |
| `AI-TRANSCRIPT.md` | AI assistance record; maintained separately |

## Run the tests

```bash
python3 -m unittest discover -s MySolution -p 'test_*.py' -v
```

Run one test module:

```bash
python3 -m unittest discover -s MySolution -p 'test_observers.py' -v
```

The supplied version has **211 passing tests** across nine modules: target, scope, Church encodings, evaluator, compiler, observers, examples, demo, and deep terms. Coverage includes capture avoidance, scope preservation, strictness, short-circuiting, recursion, purity, input preservation, exact budget boundaries, malformed observations, and CLI behavior. Tests support confidence but do not constitute a formal proof.

## Run the demonstrations

```bash
python3 MySolution/demo.py
```

By default, full generated terms are saved as `demo_terms/DEMO-XX.lambda.txt`, relative to the working directory. Each report gives the source expression, expected kind and answer, source result, term location, execution status and steps, observation status and steps, and pass/fail result. The process exits with `0` when every selected example passes and `1` otherwise.

Select examples, print terms inline, change budgets, or obtain JSON:

```bash
python3 MySolution/demo.py --example DEMO-10 --example DEMO-11
python3 MySolution/demo.py --example DEMO-01 --inline-terms
python3 MySolution/demo.py --execution-budget 20000 --observation-budget 20000
python3 MySolution/demo.py --terms-dir demo_terms --json
```

| ID | Expression | Expected result |
|---|---|---|
| DEMO-01 | `2 + 3 * 4` | `14` |
| DEMO-02 | `2 - 5` | `0` |
| DEMO-03 | `if 2 <= 3 then 7 else 9` | `7` |
| DEMO-04 | `let x = 3 in (lam y. x + y) 4` | `7` |
| DEMO-05 | `fst (pair 2 true)` | `2` |
| DEMO-06 | `snd (pair 2 true)` | `true` |
| DEMO-07 | `(lam f. f 3) (lam x. x + 1)` | `4` |
| DEMO-08 | `if true then 1 else LOOP` | `1` |
| DEMO-09 | `(lam x. 0) LOOP` | Execution exhaustion |
| DEMO-10 | Factorial of `4` | `24` |
| DEMO-11 | Fibonacci of `5` | `5` |
| DEMO-12 | `LOOP` | Execution exhaustion |
| DEMO-13 | `true and false` | `false` |
| DEMO-14 | `false or true` | `true` |

All 14 demonstrations pass with their default budgets. `LOOP` is `(fix loop(x). loop x) 0`.

## Interfaces and outcomes

- `compile_expr(expression)` returns a validated target AST without executing it. It supports open source expressions and traverses unused branches and function bodies.
- `evaluate(source_expression)` returns a source value. Source execution is unbounded.
- `evaluate(target_term, budget)` returns `EvaluationResult(status, term, steps)`. Target execution requires a closed term and a nonnegative integer budget.
- `observe(value, kind, budget)` returns `ObservationResult(status, value, steps, message)`. Kinds are `'nat'`, `'bool'`, or `('pair', leftKind, rightKind)`, including nested pairs.

Execution statuses are `completed` and `exhausted`; observation adds `malformed`. Invalid API budgets and kinds raise errors. Observation returns no decoded value when exhausted or malformed.

Target execution uses weak, left-to-right call-by-value and counts only beta-value contractions. A lambda completes in zero steps, and reaching a value on the final permitted step counts as completion. Observation receives its own budget, shared across its projections and component decoding. The demo observes the completed execution value, so execution is not charged twice.

Defaults are **10,000 execution steps and 10,000 observation steps** per example. DEMO-09 and DEMO-12 instead use **200 execution steps**. Their unbounded source evaluation is skipped. Budget exhaustion is a bounded outcome, not proof of nontermination.

## Supported language and limitations

Supported operators are unary `not` and binary `+`, `-`, `*`, `<`, `<=`, `>`, `>=`, `==`, `!=`, `and`, and `or`. Subtraction truncates at zero. Compilation rejects negative literals, unsupported operators, and invalid identifiers. Names follow `[A-Za-z_][A-Za-z0-9_]*`; encoding names such as `PLUS` are not reserved.

There is no parser, web interface, or source type checker. Source programs are constructed as ASTs. Correctness comparisons assume appropriately typed source programs. Observers interpret values using a supplied kind and are not a general type checker for arbitrary untyped lambda terms. Church computation can require substantial time and memory; beta-step budgets do not bound traversal cost or term size. Target operations use explicit stacks, but deeply nested source compilation/evaluation, source visitors, and nested-pair observation can still reach Python recursion limits.

## Presentation and attribution

- Slides: `MySolution/slides.pdf` contains the slideshow. 
- Recording: `MySolution/record.mp4` contains the recording.
- AI assistance: AI consultation, meaningful suggestions, and edits are documented in `AI-TRANSCRIPT.md`.
- `lambda1_vp.py` is supplied course code. `visitors.py` reuses Assignment 5 work. Church encodings and `Z` are standard constructions; record any specific external sources actually consulted in the final attribution record.
