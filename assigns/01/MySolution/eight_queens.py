##########################################################################
# Translated Python 3 code
##########################################################################

import sys


# ATS optimizes the original tail-recursive search; Python does not.
sys.setrecursionlimit(100_000)

N = 8


def print_dots(i: int) -> None:
    """Print i empty-board markers, matching the ATS output format."""
    if i > 0:
        print(". ", end="")
        print_dots(i - 1)


def print_row(i: int) -> None:
    print_dots(i)
    print("Q ", end="")
    print_dots(N - i - 1)
    print()


def print_board(board: tuple[int, ...]) -> None:
    for column in board:
        print_row(column)
    print()


def board_get(board: tuple[int, ...], i: int) -> int:
    """Return a board entry, or -1 for an invalid row as in the ATS code."""
    if 0 <= i < N:
        return board[i]
    return -1


def board_set(board: tuple[int, ...], i: int, j: int) -> tuple[int, ...]:
    """Return a new board with row i assigned to column j."""
    if 0 <= i < N:
        updated_board = list(board)
        updated_board[i] = j
        return tuple(updated_board)
    return board


def safety_test1(i0: int, j0: int, i1: int, j1: int) -> bool:
    """Test whether two queens can coexist without attacking each other."""
    return j0 != j1 and abs(i0 - i1) != abs(j0 - j1)


def safety_test2(i0: int, j0: int, board: tuple[int, ...], i: int) -> bool:
    """Test a candidate queen against all previously placed queens."""
    if i >= 0:
        if safety_test1(i0, j0, i, board_get(board, i)):
            return safety_test2(i0, j0, board, i - 1)
        return False
    return True


def search(board: tuple[int, ...], i: int, j: int, nsol: int) -> int:
    """Depth-first search that prints every solution and returns its count."""
    if j < N:
        if safety_test2(i, j, board, i - 1):
            board1 = board_set(board, i, j)
            if i + 1 == N:
                print(f"Solution #{nsol + 1}:\n")
                print_board(board1)
                return search(board, i, j + 1, nsol + 1)
            return search(board1, i + 1, 0, nsol)
        return search(board, i, j + 1, nsol)

    if i > 0:
        return search(board, i - 1, board_get(board, i - 1) + 1, nsol)
    return nsol


def main() -> int:
    return search((0,) * N, 0, 0, 0)


if __name__ == "__main__":
    main()

test_case_1()
test_case_2()
test_case_3()