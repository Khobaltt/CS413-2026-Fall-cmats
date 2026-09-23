"""Tests for the LAMBDA0 translation of the ATS2 eight-queens solver
(queens_source.txt / queens_lambda0.py).

Run with: python3 MySolution/TEST/test03_queens.py
Requires Python 3.12 or later, like lambda0.py.

Known correct solution counts for the N-queens problem (used as the
ground truth these tests check the interpreted search against):
N = 1 2 3 4 5  6 7  8
    1 0 0 2 10 4 40 92
"""

import os
import sys
import unittest
from pathlib import Path

# Allow this file to run directly from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mstr, T0Mpair, T0Mvar, T0Mlam, T0Mfix, T0Mapp,
    t0erm_cbv_evaluate0,
)
from queens_lambda0 import (
    NIL, mk_int_list, list_get, list_set,
    safety_test1, safety_test2,
    build_queens_term, solve_queens,
    term_int_list_to_py, term_board_list_to_py,
    is_valid_board,
)

# Known solution counts for N-queens, N = 0..8 (N = 0 is the trivial
# empty board -- included only for completeness, not exercised below).
KNOWN_SOLUTION_COUNTS = {0: 1, 1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92}

#######################################################################################################################
# 1. Board representation: the LAMBDA0 cons-list translation of ATS's
#    `board_get`/`board_set`, i.e. list_get/list_set.
#######################################################################################################################
class TestBoardRepresentation(unittest.TestCase):
    def test_mk_int_list_round_trips(self):
        t = mk_int_list([5, 3, 0, 7])
        self.assertEqual(term_int_list_to_py(t), [5, 3, 0, 7])

    def test_empty_list_is_nil(self):
        t = mk_int_list([])
        self.assertEqual(t, NIL)
        self.assertEqual(term_int_list_to_py(t), [])

    def test_list_get_reads_every_position(self):
        board = mk_int_list([4, 1, 3, 0, 2])
        for idx, expected in enumerate([4, 1, 3, 0, 2]):
            got = t0erm_cbv_evaluate0(list_get(board, T0Mint(idx)))
            self.assertEqual(got, T0Mint(expected))

    def test_list_set_updates_one_position_only(self):
        board = mk_int_list([0, 0, 0, 0])
        updated = t0erm_cbv_evaluate0(list_set(board, T0Mint(2), T0Mint(9)))
        self.assertEqual(term_int_list_to_py(updated), [0, 0, 9, 0])

    def test_list_set_then_get_agrees(self):
        board = mk_int_list([7, 7, 7, 7, 7])
        updated = list_set(board, T0Mint(3), T0Mint(1))
        got = t0erm_cbv_evaluate0(list_get(updated, T0Mint(3)))
        self.assertEqual(got, T0Mint(1))

    def test_list_set_preserves_other_positions_after_several_updates(self):
        board = mk_int_list([0, 0, 0, 0, 0, 0])
        board = list_set(board, T0Mint(0), T0Mint(3))
        board = list_set(board, T0Mint(5), T0Mint(1))
        board = list_set(board, T0Mint(2), T0Mint(4))
        got = t0erm_cbv_evaluate0(board)
        self.assertEqual(term_int_list_to_py(got), [3, 0, 4, 0, 0, 1])

#######################################################################################################################
# 2. Conflict-checking logic: LAMBDA0 translations of ATS's
#    `safety_test1` (single pair of queens) and `safety_test2`
#    (one queen against every already-placed row).
#######################################################################################################################
class TestSafetyTest1(unittest.TestCase):
    def _check(self, i0, j0, i1, j1, expected):
        term = safety_test1(T0Mint(i0), T0Mint(j0), T0Mint(i1), T0Mint(j1))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mbtf(expected))

    def test_same_column_conflicts(self):
        # Different rows, same column: unsafe regardless of row gap.
        self._check(0, 3, 5, 3, False)

    def test_same_diagonal_conflicts(self):
        # |i0-i1| == |j0-j1| : unsafe.
        self._check(2, 2, 5, 5, False)
        self._check(4, 1, 1, 4, False)  # anti-diagonal

    def test_no_conflict(self):
        self._check(0, 0, 1, 2, True)

    def test_same_row_same_column_is_a_conflict(self):
        # Degenerate case (i0==i1, j0==j1): same column -> unsafe.
        self._check(3, 3, 3, 3, False)

    def test_adjacent_rows_far_apart_columns_is_safe(self):
        self._check(0, 0, 1, 7, True)


class TestSafetyTest2(unittest.TestCase):
    def test_new_queen_safe_against_empty_prefix(self):
        # i == -1 means "no rows placed yet": always safe.
        board = mk_int_list([0, 0, 0, 0])
        term = safety_test2(T0Mint(2), T0Mint(5), board, T0Mint(-1))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mbtf(True))

    def test_new_queen_conflicts_with_one_earlier_row(self):
        # Row 0 has a queen at column 3; testing a queen at (row 2, col 3)
        # against rows [0] must find the shared column.
        board = mk_int_list([3, 0, 0, 0])
        term = safety_test2(T0Mint(2), T0Mint(3), board, T0Mint(0))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mbtf(False))

    def test_new_queen_conflicts_via_diagonal_with_a_later_checked_row(self):
        # rows placed so far: row0 col1, row1 col5 (both fine vs a queen
        # at row3 col?) -- but row2 col4 is on the diagonal from row3 col3.
        board = mk_int_list([1, 5, 4, 0])
        term = safety_test2(T0Mint(3), T0Mint(3), board, T0Mint(2))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mbtf(False))

    def test_new_queen_safe_against_several_earlier_rows(self):
        # Classic partial solution prefix: columns 0,4,7,5,2 (rows 0..4);
        # column 6 in row 5 is safe against all of them.
        board = mk_int_list([0, 4, 7, 5, 2, 0])
        term = safety_test2(T0Mint(5), T0Mint(6), board, T0Mint(4))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mbtf(True))

    def test_checks_every_row_not_just_the_nearest(self):
        # Safe against rows 1 and 2 individually, but row 0 (column 6)
        # shares the new queen's column -- must be caught even though
        # it is the row furthest from the one being tested.
        board = mk_int_list([6, 1, 2, 0])
        term = safety_test2(T0Mint(3), T0Mint(6), board, T0Mint(2))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mbtf(False))

#######################################################################################################################
# 3. The full translated search, on board sizes small enough to run
#    quickly, checked against the known N-queens solution counts.
#######################################################################################################################
class TestSmallBoards(unittest.TestCase):
    def test_n_equals_1_trivial_solution(self):
        count, boards = solve_queens(1)
        self.assertEqual(count, KNOWN_SOLUTION_COUNTS[1])
        self.assertEqual(boards, [[0]])

    def test_n_equals_2_no_solutions(self):
        count, boards = solve_queens(2)
        self.assertEqual(count, KNOWN_SOLUTION_COUNTS[2])
        self.assertEqual(boards, [])

    def test_n_equals_3_no_solutions(self):
        count, boards = solve_queens(3)
        self.assertEqual(count, KNOWN_SOLUTION_COUNTS[3])
        self.assertEqual(boards, [])

    def test_n_equals_4_two_solutions(self):
        count, boards = solve_queens(4)
        self.assertEqual(count, KNOWN_SOLUTION_COUNTS[4])
        self.assertEqual(len(boards), 2)

    def test_n_equals_5_ten_solutions(self):
        count, boards = solve_queens(5)
        self.assertEqual(count, KNOWN_SOLUTION_COUNTS[5])
        self.assertEqual(len(boards), 10)

    def test_n_equals_6_four_solutions(self):
        count, boards = solve_queens(6)
        self.assertEqual(count, KNOWN_SOLUTION_COUNTS[6])
        self.assertEqual(len(boards), 4)

    def test_solution_count_matches_number_of_recorded_boards(self):
        # The interpreted nsol counter and the interpreted sols list are
        # built independently (one incremented, one consed) every time a
        # solution is found; they should always agree.
        for n in (1, 4, 5, 6):
            count, boards = solve_queens(n)
            self.assertEqual(count, len(boards))

#######################################################################################################################
# 4. Every board the interpreted search returns must actually be a
#    valid N-queens placement: one queen per row (guaranteed by
#    construction), no shared column, no shared diagonal.
#######################################################################################################################
class TestSolutionValidity(unittest.TestCase):
    def test_is_valid_board_accepts_a_real_solution(self):
        # A known 4-queens solution.
        self.assertTrue(is_valid_board([1, 3, 0, 2]))

    def test_is_valid_board_rejects_shared_column(self):
        self.assertFalse(is_valid_board([0, 0, 1, 2]))

    def test_is_valid_board_rejects_shared_diagonal(self):
        self.assertFalse(is_valid_board([0, 1, 2, 3]))

    def test_all_n4_solutions_are_valid_and_distinct(self):
        _, boards = solve_queens(4)
        self.assertTrue(all(is_valid_board(b) for b in boards))
        self.assertEqual(len({tuple(b) for b in boards}), len(boards))

    def test_all_n5_solutions_are_valid_and_distinct(self):
        _, boards = solve_queens(5)
        self.assertTrue(all(is_valid_board(b) for b in boards))
        self.assertEqual(len({tuple(b) for b in boards}), len(boards))

    def test_all_n6_solutions_are_valid_and_distinct(self):
        _, boards = solve_queens(6)
        self.assertTrue(all(is_valid_board(b) for b in boards))
        self.assertEqual(len({tuple(b) for b in boards}), len(boards))

    def test_every_row_is_represented_exactly_once(self):
        # Each solution board has exactly one entry per row by
        # construction (it is built one T0Mlam-driven row at a time),
        # so its length must equal N.
        for n in (4, 5, 6):
            _, boards = solve_queens(n)
            self.assertTrue(all(len(b) == n for b in boards))

#######################################################################################################################
# 5. The translated program is a *closed* term: check the term built
#    by build_queens_term has no unbound variables, i.e. it satisfies
#    the interpreter's no-capture-under-substitution assumption.
#######################################################################################################################
class TestClosedTerm(unittest.TestCase):
    def test_queens_term_is_closed(self):
        from lambda0 import t0erm_fvset
        term = build_queens_term(4)
        self.assertEqual(t0erm_fvset(term), frozenset())

    def test_queens_term_of_various_sizes_is_closed(self):
        from lambda0 import t0erm_fvset
        for n in (1, 3, 5, 8):
            term = build_queens_term(n)
            self.assertEqual(t0erm_fvset(term), frozenset())

#######################################################################################################################
# 6. The full eight-queens board, matching the ATS2 source's #define N 8.
#    This is by far the slowest and most memory-hungry test in the
#    suite: t0erm_cbv_evaluate0 is a plain recursive (non-memoized,
#    non-tail-call-optimized) Python evaluator, so the very large
#    backtracking search that enumerates every 8-queens solution can
#    take many minutes and a large amount of stack/heap. It is skipped
#    by default; set RUN_QUEENS_N8=1 to run it (with enough time and
#    memory available). See README.md ("Limitations") for the full
#    discussion, and TestSmallBoards / TestSolutionValidity above for
#    N = 1..6 run and checked directly.
#######################################################################################################################
@unittest.skipUnless(
    os.environ.get("RUN_QUEENS_N8") == "1",
    "full N=8 search is slow/memory-heavy under this tree-walking interpreter; "
    "set RUN_QUEENS_N8=1 to run it",
)
class TestEightQueens(unittest.TestCase):
    # solve_queens(8) is run once for the whole class (not once per test
    # method) since each run costs several minutes of wall-clock time.
    @classmethod
    def setUpClass(cls):
        cls.count, cls.boards = solve_queens(8)

    def test_n_equals_8_matches_known_solution_count(self):
        self.assertEqual(self.count, KNOWN_SOLUTION_COUNTS[8])
        self.assertEqual(len(self.boards), 92)

    def test_n_equals_8_solutions_all_valid_and_distinct(self):
        self.assertTrue(all(is_valid_board(b) for b in self.boards))
        self.assertEqual(len({tuple(b) for b in self.boards}), len(self.boards))


if __name__ == "__main__":
    unittest.main(verbosity=2)