Eight-queens: ATS2 to Lambda0
==============================

Running the program

  python3 MySolution/queens_lambda0.py
      solves 6-queens (fast demo)

  python3 MySolution/queens_lambda0.py 8
      solves 8-queens, matching "#define N 8" (slow: see Limitations)

  python3 MySolution/TEST/test02_lambda0.py -v

  python3 MySolution/TEST/test03_queens.py -v
      everything except the N=8 test

  RUN_QUEENS_N8=1 python3 MySolution/TEST/test03_queens.py -v
      also attempts the full N=8 search

Both scripts require Python 3.12+ (for the "type" statement used in
lambda0.py), same as the starter code.


Mapping ATS2 to Lambda0

int8 (an 8-tuple of columns, bd.0 .. bd.7)
  -> a cons-list: T0Mpair(head, tail), terminated by the sentinel NIL = T0Mstr("nil"). mk_int_list([...]) builds one from a Python list.

board_get(bd, i)  (linear if/else chain indexing into the tuple)
  -> list_get, a T0Mfix that recurses on the index: fix lg(i). lam l. if i==0 then, fst(l), else lg(i-1)(snd l). The ATS if/else chain is an unrolled "get nth element of a list", so this is a direct, general translation of the same idea.

board_set(bd, i, j)  (linear if/else chain, rebuilding the tuple)
  -> list_set, structurally the same recursion as list_get, rebuilding each cons cell on the way back up: fix ls(i). lam l. lam v. if i==0, then (v, snd l), else (fst l, ls(i-1)(snd l) v)

abs (...)
  -> a plain (non-recursive) T0Mlam: lam x. if x < 0, then -x else x using the existing unary "-" operator and "<" comparison. Not a recursive function, so T0Mfix isn't needed for it.

andalso  (short-circuit boolean and)
  -> AND(a, b) = T0Mif0(a, b, T0Mbtf(False)) Under call-by-value, T0Mif0 only evaluates the branch it selects, so this reproduces andalso's short-circuiting exactly: if a is False, then b is never evaluated.

safety_test1(i0, j0, i1, j1)  (no recursion)
  -> a plain curried T0Mlam chain: lam i0. lam j0. lam i1. lam j1. (j0 != j1) AND (abs(i0-i1) != abs(j0-j1))

safety_test2(i0, j0, bd, i)  (recurses on i, walking backward through already-placed rows)
  -> a T0Mfix whose bound argument is i (the value that actually changes across recursive calls); i0, j0, bd are curried afterwards and re-supplied, unchanged, on every recursive call: fix st2(i). lam i0. lam j0. lam bd. if i>=0, then (safety_test1(...), then st2(i-1) i0 j0 bd else false), else true

search(bd, i, j, nsol)  (recurses on all four arguments at once)
  -> Since T0Mfix only binds ONE argument, the whole state is packed into a single right-nested tuple (bd, (i, (j, (nsol, sols)))) and unpacked with chains of T0Mpfst/T0Mpsnd (st_bd, st_i, st_j, st_nsol, st_sols in queens_lambda0.py). The recursive function is fix srch(s). ..., and every recursive call is srch(new_state) with a freshly built 5-tuple. The control flow (three nested ifs: j<N? safe? i+1=N?, then the backtracking else branch) is copied one-for-one from the ATS source.

print!(...) / print_board  (printing every solution as it is found)
  -> LAMBDA0 has no I/O, so "print the solution" becomes "cons the completed board onto an accumulator list, sols". sols is the fifth component of the packed search state above. The final answer is T0Mpair(nsol, sols): the count and every board found, in the order the search found them. This preserves the ATS program's behavior of enumerating (not just counting, and not stopping at the first solution) every solution.

search's final "else nsol"  (loop terminates: i==0 and j>=N)
  -> the one place the fixed-point function does not call itself again: it directly returns T0Mpair(nsol, sols) instead of recursing on a new state. Every other branch calls srch again.


Comparison with the Original ATS2 Program

The ATS2 search function enumerates every solution (it never stops after the first: on placing the last queen it prints the board and then keeps trying other columns in the last row, backtracking through the whole tree), and its final return value nsol is the total solution count. The Lambda0 translation reproduces this: it also enumerates every solution (via the sols accumulator) and also returns a total count (nsol), computed independently (nsol is incremented on each solution and sols is separately consed: test_solution_count_matches_number_of_recorded_boards checks the two agree).

For every N (1-7) that was run in testing, the interpreted Lambda0 search produced exactly the known correct solution count, and every returned board was independently checked (is_valid_board) to have no two queens sharing a row (guaranteed by construction: each board has exactly one entry per row index), column, or diagonal, with no
duplicate boards. This is strong evidence that the translation accurately reproduces the ATS2 algorithm: board_get / board_set, safety_test1, safety_test2, and search's control flow were all translated structurally (same recursion structure), which is also why TestSafetyTest1 / TestSafetyTest2 in test03_queens.py exercise the conflict-checking terms directly (same-column, same-diagonal, anti-diagonal, and multi-row prefixes), independent of the full search.


Limitations of Lambda0

Performance: t0erm_cbv_evaluate0 is a plain, non-memoized, recursive Python function with no tail-call optimization. Every Lambda0-level recursive call of search (or safety_test2, or list_get/list_set) costs several nested Python stack frames that only unwind once the entire rest of the computation has finished. Larger N values increase the runtime extremely quickly, making the N=8 case take unreasonably long to complete. test03_queens.py's TestEightQueens class is therefore skipped by default and only runs with RUN_QUEENS_N8=1 set, given enough time (and memory) budget. N=1-7 are all tested unconditionally and all match the known solution counts.

No true "let": Lambda0 has no let-binding construct, so ATS's local "let ... in ... end" blocks (e.g. board_set's destructuring "let val (x0,...,x7) = bd in ...") are translated either as immediately-applied T0Mlams (where a genuine binding was needed) or, where the "let-bound" name was just a readability aid for a value already available as a variable (e.g. test, bd1 in search), simply inlined at each use site, since re-projecting a pair/tuple has no side effects and is cheap.

No output: Printing is modeled as accumulating solutions into a list rather than any actual output; the Lambda0 program's "output" is its final return value.

Fixed-size lists, not true 8-tuples: The cons-list representation is not statically length-8 the way ATS's int8 type is; nothing in the interpreter enforces board length, so list_get/list_set would accept an out-of-range index the same way the ATS "else ~1" / "else bd" fallback arms do for out-of-range i (both are "best effort", not type-enforced).


Reviewing AI Code

First, I made sure that I had a working understanding of the code AI wrote and the code surrounding it. I compared its behavior to the expected behavior using very granular test cases. This helped me to make sure that each section of code was working as expected. My test cases were designed to test different inputs, including edge cases and input types. 