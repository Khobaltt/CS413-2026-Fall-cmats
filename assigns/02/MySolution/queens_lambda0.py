"""Translate the ATS2 eight-queens solver (queens_source.txt) into a
LAMBDA0 term of type `t0erm`, and run it with the extended
`t0erm_cbv_evaluate0` interpreter from lambda0.py.

Run with: python3 MySolution/queens_lambda0.py
Requires Python 3.12 or later, like lambda0.py.

--------------------------------------------------------------------
Representation choices (see README.md for the full discussion)
--------------------------------------------------------------------

* Board (ATS `int8`, a fixed 8-tuple of columns indexed by row):
    represented as a cons-list built from T0Mpair, terminated by the
    sentinel value NIL = T0Mstr("nil"). `board[i]` (ATS `board_get`)
    becomes `list_get(board, i)`, and `board_set` becomes `list_set`.
    Both are written as LAMBDA0 T0Mfix functions that recurse on the
    index, exactly mirroring the linear if/else chain of
    `board_get`/`board_set` in the ATS source (that chain is really a
    hand-unrolled "get/set nth element of a list").

* Search state (ATS `search`'s four arguments `bd, i, j, nsol`, plus
    one extra accumulator described below): T0Mfix only binds a single
    argument, so the whole state is packed into one right-nested tuple
    of pairs `(bd, (i, (j, (nsol, sols))))` and unpacked with chains of
    T0Mpfst/T0Mpsnd. `sols` is a LAMBDA0 list of every solution board
    found, added to mirror the ATS program's behaviour of printing
    every solution as it is discovered (LAMBDA0 has no I/O, so
    "printing" a solution becomes "consing it onto an accumulator").

* Booleans: T0Mbtf, produced by comparisons (already supported by the
    starter interpreter's T0Mop2 for <,>,<=,>=,==,!=) and by T0Mif0.
    ATS's short-circuiting `andalso` becomes
    `T0Mif0(a, b, T0Mbtf(False))`, which only evaluates `b` under CBV
    when `a` is true -- the same short-circuit behaviour.

* `abs`: not a primitive in the starter interpreter, but it does not
    need to become one -- it is defined as an ordinary (non-recursive)
    LAMBDA0 T0Mlam using the existing unary "-" operator and "<".

No new primitive operations were added to the interpreter: every
operator `search`/`safety_test1`/`safety_test2` needs (+, -, ==, !=,
<, >, <=, >=) was already implemented in the T0Mop1/T0Mop2 cases of
`t0erm_cbv_evaluate0` supplied with lambda0.py.
"""

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lambda0 import (
    T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mint, T0Mbtf, T0Mstr, T0Mop1, T0Mop2,
    T0Mif0, T0Mpair, T0Mpfst, T0Mpsnd,
    t0erm_cbv_evaluate0,
)

########################################################################
# Small term-building helpers
########################################################################

def V(name):
    return T0Mvar(name)

def AND(a, b):
    """Short-circuiting AND: matches ATS's `andalso` under CBV, since
    T0Mif0 only evaluates the branch it selects."""
    return T0Mif0(a, b, T0Mbtf(False))

NIL = T0Mstr("nil")

def is_nil_term(t):
    return isinstance(t, T0Mstr) and t.arg1 == "nil"

def cons(head, tail):
    return T0Mpair(head, tail)

def mk_int_list(pyints):
    t = NIL
    for x in reversed(pyints):
        t = cons(T0Mint(x), t)
    return t

########################################################################
# abs, as a plain (non-recursive) LAMBDA0 function: lambda x. if x < 0
# then -x else x
########################################################################

ABS = T0Mlam("x", T0Mif0(
    T0Mop2("<", V("x"), T0Mint(0)),
    T0Mop1("-", V("x")),
    V("x"),
))

def abs_of(x_term):
    return T0Mapp(ABS, x_term)

########################################################################
# list_get / list_set: LAMBDA0 translations of `board_get`/`board_set`.
# Both recurse (via T0Mfix) on the index, walking down the cons-list
# with T0Mpsnd exactly as the ATS if/else chain walks down the tuple
# positions.
########################################################################

# list_get = fix lg(i). lam l. if i == 0 then fst(l) else lg (i-1) (snd l)
LIST_GET = T0Mfix("lg", "i", T0Mlam("l",
    T0Mif0(
        T0Mop2("==", V("i"), T0Mint(0)),
        T0Mpfst(V("l")),
        T0Mapp(T0Mapp(V("lg"), T0Mop2("-", V("i"), T0Mint(1))), T0Mpsnd(V("l"))),
    )
))

def list_get(l_term, i_term):
    return T0Mapp(T0Mapp(LIST_GET, i_term), l_term)

# list_set = fix ls(i). lam l. lam v.
#   if i == 0 then (v, snd l) else (fst l, ls (i-1) (snd l) v)
LIST_SET = T0Mfix("ls", "i", T0Mlam("l", T0Mlam("v",
    T0Mif0(
        T0Mop2("==", V("i"), T0Mint(0)),
        T0Mpair(V("v"), T0Mpsnd(V("l"))),
        T0Mpair(
            T0Mpfst(V("l")),
            T0Mapp(T0Mapp(T0Mapp(V("ls"), T0Mop2("-", V("i"), T0Mint(1))), T0Mpsnd(V("l"))), V("v")),
        ),
    )
)))

def list_set(l_term, i_term, v_term):
    return T0Mapp(T0Mapp(T0Mapp(LIST_SET, i_term), l_term), v_term)

########################################################################
# safety_test1(i0, j0, i1, j1) = j0 != j1 andalso
#                                 abs(i0-i1) != abs(j0-j1)
# A plain (non-recursive) curried LAMBDA0 function.
########################################################################

SAFETY_TEST1 = T0Mlam("i0", T0Mlam("j0", T0Mlam("i1", T0Mlam("j1",
    AND(
        T0Mop2("!=", V("j0"), V("j1")),
        T0Mop2(
            "!=",
            abs_of(T0Mop2("-", V("i0"), V("i1"))),
            abs_of(T0Mop2("-", V("j0"), V("j1"))),
        ),
    )
))))

def safety_test1(i0, j0, i1, j1):
    return T0Mapp(T0Mapp(T0Mapp(T0Mapp(SAFETY_TEST1, i0), j0), i1), j1)

########################################################################
# safety_test2(i0, j0, bd, i):
#   if i >= 0 then
#     safety_test1(i0,j0,i,board_get(bd,i)) andalso safety_test2(i0,j0,bd,i-1)
#   else true
#
# The ATS source writes this the other way around (calls
# safety_test2 only *inside* the then-branch of the safety_test1
# check), which is logically the same short-circuit as an `andalso`
# chain; we keep the ATS structure (nested T0Mif0) rather than folding
# it into AND, to mirror the source as closely as possible.
#
# T0Mfix binds a single argument; `i` (the value that changes on every
# recursive call) is that bound argument, and i0/j0/bd are threaded
# through as curried lambdas re-applied, unchanged, on each recursive
# call.
########################################################################

ST2 = T0Mfix("st2", "i", T0Mlam("i0", T0Mlam("j0", T0Mlam("bd",
    T0Mif0(
        T0Mop2(">=", V("i"), T0Mint(0)),
        T0Mif0(
            safety_test1(V("i0"), V("j0"), V("i"), list_get(V("bd"), V("i"))),
            T0Mapp(
                T0Mapp(T0Mapp(T0Mapp(V("st2"), T0Mop2("-", V("i"), T0Mint(1))), V("i0")), V("j0")),
                V("bd"),
            ),
            T0Mbtf(False),
        ),
        T0Mbtf(True),
    )
))))

def safety_test2(i0, j0, bd, i):
    return T0Mapp(T0Mapp(T0Mapp(T0Mapp(ST2, i), i0), j0), bd)

########################################################################
# search state: (bd, (i, (j, (nsol, sols))))
########################################################################

def mk_state(bd, i, j, nsol, sols):
    return T0Mpair(bd, T0Mpair(i, T0Mpair(j, T0Mpair(nsol, sols))))

def st_bd(s):   return T0Mpfst(s)
def st_i(s):    return T0Mpfst(T0Mpsnd(s))
def st_j(s):    return T0Mpfst(T0Mpsnd(T0Mpsnd(s)))
def st_nsol(s): return T0Mpfst(T0Mpsnd(T0Mpsnd(T0Mpsnd(s))))
def st_sols(s): return T0Mpsnd(T0Mpsnd(T0Mpsnd(T0Mpsnd(s))))

########################################################################
# search(bd, i, j, nsol):
#
#   if j < N then
#     let test = safety_test2(i, j, bd, i-1) in
#     if test then
#       let bd1 = board_set(bd, i, j) in
#       if i+1 = N
#         then (print solution; search(bd, i, j+1, nsol+1))
#         else search(bd1, i+1, 0, nsol)
#     else search(bd, i, j+1, nsol)
#   else
#     if i > 0
#       then search(bd, i-1, board_get(bd, i-1)+1, nsol)
#       else nsol
#
# LAMBDA0 translation: same shape, threaded through the packed state
# tuple above. "print solution" becomes "cons the completed board onto
# the sols accumulator" (there is no I/O in LAMBDA0). The terminal
# case ("else nsol") returns the final answer as a pair (nsol, sols)
# instead of recursing again -- this is the only place the fix-point
# does *not* apply itself again.
########################################################################

def build_search_fix(n):
    s = V("s")
    bd, i, j, nsol, sols = st_bd(s), st_i(s), st_j(s), st_nsol(s), st_sols(s)

    bd1 = list_set(bd, i, j)  # board with the new queen placed at (i, j)

    # i+1 = N: last row just got a queen -> record the solution and
    # keep searching this row for further columns (bd is unchanged,
    # exactly as in the ATS source: `search (bd, i, j+1, nsol+1)`).
    last_row_new_state = mk_state(
        bd, i, T0Mop2("+", j, T0Mint(1)), T0Mop2("+", nsol, T0Mint(1)), cons(bd1, sols)
    )
    # otherwise: move on to row i+1, column 0, carrying bd1 forward.
    next_row_new_state = mk_state(bd1, T0Mop2("+", i, T0Mint(1)), T0Mint(0), nsol, sols)

    placed_branch = T0Mif0(
        T0Mop2("==", T0Mop2("+", i, T0Mint(1)), T0Mint(n)),
        last_row_new_state,
        next_row_new_state,
    )
    fail_branch = mk_state(bd, i, T0Mop2("+", j, T0Mint(1)), nsol, sols)

    j_in_range_branch = T0Mif0(
        safety_test2(i, j, bd, T0Mop2("-", i, T0Mint(1))),
        T0Mapp(V("srch"), placed_branch),
        T0Mapp(V("srch"), fail_branch),
    )

    backtrack_new_state = mk_state(
        bd,
        T0Mop2("-", i, T0Mint(1)),
        T0Mop2("+", list_get(bd, T0Mop2("-", i, T0Mint(1))), T0Mint(1)),
        nsol,
        sols,
    )
    terminal_result = T0Mpair(nsol, sols)

    j_out_of_range_branch = T0Mif0(
        T0Mop2(">", i, T0Mint(0)),
        T0Mapp(V("srch"), backtrack_new_state),
        terminal_result,
    )

    body = T0Mif0(T0Mop2("<", j, T0Mint(n)), j_in_range_branch, j_out_of_range_branch)
    return T0Mfix("srch", "s", body)

def build_queens_term(n):
    """Build the closed LAMBDA0 term that solves the n-queens problem
    (N baked into the term at construction time, matching ATS's
    `#define N 8`)."""
    search_fix = build_search_fix(n)
    initial_board = mk_int_list([0] * n)  # placeholder columns for unplaced rows
    initial_state = mk_state(initial_board, T0Mint(0), T0Mint(0), T0Mint(0), NIL)
    return T0Mapp(search_fix, initial_state)

########################################################################
# Helpers to turn a LAMBDA0 result back into plain Python data, purely
# for reporting/checking -- these do not perform any part of the
# search themselves, they only walk an already-fully-evaluated value.
########################################################################

def term_int_list_to_py(t):
    out = []
    while not is_nil_term(t):
        if not isinstance(t, T0Mpair) or not isinstance(t.arg1, T0Mint):
            raise TypeError(f"term_int_list_to_py: malformed list ({t})")
        out.append(t.arg1.arg1)
        t = t.arg2
    return out

def term_board_list_to_py(t):
    out = []
    while not is_nil_term(t):
        if not isinstance(t, T0Mpair):
            raise TypeError(f"term_board_list_to_py: malformed list ({t})")
        out.append(term_int_list_to_py(t.arg1))
        t = t.arg2
    return out

########################################################################
# Running the interpreter: the search explores a real (if small)
# backtracking tree, and t0erm_cbv_evaluate0 is a plain recursive
# (non-tail-call-optimized) Python function, so each LAMBDA0-level
# recursive call of `search` costs several nested Python stack frames.
# We run it on a thread with a generous stack and a raised recursion
# limit so N up to 8 can be evaluated.
########################################################################

def _run_with_big_stack(f, *args, **kwargs):
    box = {}
    def wrapper():
        try:
            box["value"] = f(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001 - re-raised on the caller's thread
            box["error"] = e

    old_limit = sys.getrecursionlimit()
    old_stack_size = threading.stack_size()
    sys.setrecursionlimit(1_000_000)
    threading.stack_size(512 * 1024 * 1024)
    try:
        t = threading.Thread(target=wrapper)
        t.start()
        t.join()
    finally:
        sys.setrecursionlimit(old_limit)
        threading.stack_size(old_stack_size)

    if "error" in box:
        raise box["error"]
    return box["value"]

def solve_queens(n):
    """Build the n-queens LAMBDA0 term and evaluate it with the
    (unmodified) interpreter. Returns (solution_count, boards), where
    `boards` is the Python-list-of-lists rendering of every solution
    the interpreted search found, in the order it found them."""
    term = build_queens_term(n)

    def _eval():
        return t0erm_cbv_evaluate0(term)

    result = _run_with_big_stack(_eval)
    if not isinstance(result, T0Mpair) or not isinstance(result.arg1, T0Mint):
        raise TypeError(f"solve_queens: unexpected result shape ({result})")
    nsol = result.arg1.arg1
    boards = term_board_list_to_py(result.arg2)
    return nsol, boards

########################################################################
# Board-validity checker, used for reporting/testing (not the search).
########################################################################

def is_valid_board(board):
    n = len(board)
    for r1 in range(n):
        for r2 in range(r1 + 1, n):
            c1, c2 = board[r1], board[r2]
            if c1 == c2:
                return False
            if abs(r1 - r2) == abs(c1 - c2):
                return False
    return True

########################################################################

def print_board(board):
    n = len(board)
    for col in board:
        print(". " * col + "Q " + ". " * (n - col - 1))

if __name__ == "__main__":
    # Default to a small, fast N for an interactive demo. `python3
    # queens_lambda0.py 8` reproduces the ATS source's `#define N 8`,
    # but be aware that N=8 can take a long time and a lot of memory
    # under this plain tree-walking interpreter -- see README.md
    # ("Limitations") before running it.
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    print(f"Solving {N}-queens with the LAMBDA0 interpreter...")
    count, boards = solve_queens(N)
    print(f"\nTotal solutions found by the interpreted search: {count}")
    print(f"Solutions recorded: {len(boards)}")
    print(f"All boards valid: {all(is_valid_board(b) for b in boards)}")
    if boards:
        print("\nFirst solution found:\n")
        print_board(boards[0])