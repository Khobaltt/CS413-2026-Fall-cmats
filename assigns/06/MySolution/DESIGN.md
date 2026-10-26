# Compiler Design

## Architecture and language boundary

The project translates the supplied extended lambda-calculus AST into pure lambda calculus. Source expressions include naturals, booleans, functions, arithmetic, comparisons, lets, pairs, conditionals, and recursive functions. The target has exactly three frozen dataclasses: `Var`, `Lam`, and `App`. The `Term` union is an annotation, not another constructor. Immutability permits safe subtree sharing and helps preserve inputs during compilation and reduction.

Responsibilities are separated across syntax, scope operations, Church builders, compilation, evaluation, observation, and demonstration modules. `compile_expr` dispatches through a subclass of the supplied `D0ExpVisitor` and validates the resulting target tree. It never imports or invokes evaluation. `evaluate` is the shared entry point for both languages: source inputs use lexical environments and source values; target inputs use capture-avoiding substitution. The supplied source interpreter is not used to implement the new source semantics.

Target printing uses the required forms `x`, `(lam x. body)`, and `(function argument)`. Validation checks exact node types and identifiers matching `[A-Za-z_][A-Za-z0-9_]*`. Open syntax is valid. Execution and observation separately enforce a closed-program policy. Encoding abbreviations remain legal user identifiers because generated encodings contain expanded syntax rather than privileged names.

## Translation rules

Let `C[e]` denote compilation. Application associates left. Uppercase combinator names below abbreviate expanded target trees; none remain as free runtime symbols. `NUM(n)` constructs the Church numeral for a nonnegative integer.

| Source form | Translation |
|---|---|
| Natural `n` | `NUM(n)` |
| `true`, `false` | `TRUE`, `FALSE` |
| Variable `x` | `x` |
| `lam x. e` | `lam x. C[e]` |
| `e1 e2` | `C[e1] C[e2]` |
| `let x = a in b` | `(lam x. C[b]) C[a]` |
| `not e` | `NOT C[e]` |
| `a + b`, `a - b`, `a * b` | `ADD C[a] C[b]`, `SUB C[a] C[b]`, `MUL C[a] C[b]` |
| `a < b`, `a <= b` | `LT C[a] C[b]`, `LEQ C[a] C[b]` |
| `a > b`, `a >= b` | `GT C[a] C[b]`, `GEQ C[a] C[b]` |
| `a == b`, `a != b` | `EQ C[a] C[b]`, `NEQ C[a] C[b]` |
| `pair a b` | `PAIR C[a] C[b]` |
| `fst e`, `snd e` | `FIRST C[e]`, `SECOND C[e]` |
| `if c then t else f` | `(C[c] (lam u. C[t]) (lam v. C[f])) I` |
| `a and b` | `(C[a] (lam u. C[b]) (lam v. FALSE)) I` |
| `a or b` | `(C[a] (lam u. TRUE) (lam v. C[b])) I` |
| `fix f(x). e` | `Z (lam f. lam x. C[e])` |

Compilation visits both branches and every function body, even when execution would skip them. Negative literals and unsupported operators therefore fail during translation wherever they occur. This validation does not execute the expression, infer types, or precompute arithmetic. Literal construction alone uses a Python loop to build the requested syntax.

## Encodings and predecessor

`church.py` returns closed target terms. Its basic encodings are:

```text
I       = lam x. x
TRUE    = lam t. lam f. t
FALSE   = lam t. lam f. f
NUM(n)  = lam f. lam x. f^n(x)
PAIR    = lam a. lam b. lam s. s a b
FIRST   = lam p. p TRUE
SECOND  = lam p. p FALSE
SUCC    = lam n. lam f. lam x. f (n f x)
ADD     = lam m. lam n. lam f. lam x. m f (n f x)
MUL     = lam m. lam n. lam f. lam x. m (n f) x
```

Predecessor tracks a pair containing the previous and current numbers. Starting from `(0, 0)`, its transition maps `(a, b)` to `(b, b + 1)`. After zero iterations the first component is zero; after a positive number `n` it is `n - 1`. Thus predecessor naturally saturates at zero. All transition work uses expanded Church pairs, selectors, and successor.

```text
TRANS   = lam p. PAIR (SECOND p) (SUCC (SECOND p))
PRED    = lam n. FIRST (n TRANS (PAIR NUM(0) NUM(0)))
SUB     = lam m. lam n. n PRED m
ISZERO  = lam n. n (lam ignored. FALSE) TRUE
NOT     = lam p. p FALSE TRUE
AND     = lam p. lam q. p q FALSE
OR      = lam p. lam q. p TRUE q
LEQ     = lam m. lam n. ISZERO (SUB m n)
GEQ     = lam m. lam n. LEQ n m
LT      = lam m. lam n. NOT (LEQ n m)
GT      = lam m. lam n. NOT (LEQ m n)
EQ      = lam m. lam n. AND (LEQ m n) (LEQ n m)
NEQ     = lam m. lam n. NOT (EQ m n)
```

The library's `AND` and `OR` accept boolean values. Source short-circuit operators instead use delayed conditional translation, so an unneeded operand is never forced.

## Scope, freshness, and substitution

`freeVariables` follows the usual variable, lambda-removal, and application-union rules. Its explicit traversal tracks counts of active binders, preserving shadowing and restoring scope between siblings. `allNames` includes every occurrence and declaration, including unused binders.

The compiler starts a new deterministic supply per `compile_expr` call. Before wrapping branches, it reserves all names in their translated subterms and the condition. It then tries `_thunk_0`, `_thunk_1`, and later candidates, skipping reserved names. This prevents capture even for open source programs using generated-looking identifiers.

Substitution uses the reused `FreshNames` policy: try `base_1`, `base_2`, and subsequent suffixes while avoiding reserved and previously generated names. One supply is initialized per substitution from relevant names. Replacement free variables are computed once. Substitution stops under a binder matching the substituted variable and renames a conflicting binder before descending. Renaming stops at nested shadowing declarations. Cached free-occurrence checks avoid repeatedly scanning unaffected subtrees. Inputs are preserved, and inserting a replacement does not trigger substitution inside that replacement.

## Evaluation and delayed control flow

Target execution is weak, left-to-right call-by-value. Lambdas are values; their bodies are not reduced. Applications evaluate the function, then argument, then contract `(lam x. body) value` by substitution. An explicit context stack finds one contraction and rebuilds surrounding applications. Only contractions count toward the budget; traversal and validation do not.

`EvaluationResult` records status, residual term or completed value, and steps. Completion is checked before exhaustion: a lambda succeeds with budget zero, and a final permitted contraction may complete successfully. Open terms and invalid budgets raise errors. Source evaluation is unbounded and uses closures with lexical scope, truncated subtraction, strict pairs and lets, and short-circuit booleans.

Ordinary Church selection would evaluate both branches under call-by-value. The compiler instead passes lambda thunks, selects one, and applies it to identity. Recursion similarly delays self-application using the expanded combinator built in `compiler.py`:

```text
Z = lam f. (lam x. f (lam v. (x x) v))
           (lam x. f (lam v. (x x) v))
```

Its extra lambda prevents immediate recursive unfolding. The translation's inner parameter binder shadows the recursive name when both names coincide, matching source environment extension order.

## Observation contracts

Weak execution can return a numeral whose body still contains work. Observers expose that work through pure contexts evaluated by the same target evaluator. Naturals are applied to:

```text
STEP = lam tail. lam c. lam z. c tail
BASE = lam c. lam z. z
```

The resulting finite spine is inspected structurally. Each STEP node contributes one; BASE terminates it. Binder relationships, rather than fixed spellings, determine valid selectors. Booleans choose between two distinct closed markers, `lam marker. marker` and `lam marker. lam inner. marker`, compared up to alpha-equivalence. Pairs are evaluated, projected left then right, and recursively observed using component kinds.

Kinds are `'nat'`, `'bool'`, or `('pair', leftKind, rightKind)`. Explicit kinds are necessary because zero and false share a representation. One observation budget covers all projections and component work. `ObservationResult` distinguishes completion, exhaustion, and malformed data; unsuccessful observations discard partial decoded results. Python inspects final shapes but performs no encoded reduction. Observers are not a general type system for arbitrary target programs.

## Correctness, evidence, and tradeoffs

The intended correctness claim applies to well-formed, appropriately typed source programs: a terminating source result agrees with observation of its compilation when both budgets suffice. A structural argument relates source values to their encodings. Variables and functions preserve binding, application preserves strict operand order, closed operator encodings implement the corresponding operations, fresh thunks preserve conditional selection, and delayed `Z` unfolds recursive calls. This is an argument outline rather than a mechanized proof. Source and target costs need not match.

Validation of this version passed 211 unit tests and all 14 demonstrations, including factorial, Fibonacci, skipped divergence, and strict-argument exhaustion. Tests also exercise purity, input preservation, shadowing, compiler independence from evaluation, budget boundaries, malformed outputs, and deep target terms. Finite tests cannot establish correctness for every program, and budget exhaustion cannot prove divergence.

Expanded terms simplify the purity boundary but increase size and reduction cost. Explicit stacks protect core target traversals from Python recursion depth, while source visitors, source evaluation, compilation, and nested-pair observation retain recursive paths. Substitution can duplicate syntax, and a beta-step budget bounds neither memory nor wall-clock work. There is no parser, optimization pass, or source type checker. These choices keep the semantic pipeline inspectable while leaving performance and static checking as future work.
