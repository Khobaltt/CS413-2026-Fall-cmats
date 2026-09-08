from eight_queens import search, N, board_get, safety_test1

##########################################################################
# Test cases
##########################################################################
 
def test_case_1():
    """Standard case: the 8-queens problem has exactly 92 solutions"""
    nsol = search((0,) * N, 0, 0, 0)
    expected = 92
    if nsol == expected:
        print("Test case 1 passed")
    else:
        print("Test case 1 failed")
    print("Expected 92 solutions and found", nsol, "solutions\n")
 
def test_case_2():
    """Edge case: indices outside (0, ..., N-1) must return -1, matching the ATS 'else ~1' branch that safety_test2 relies on when it calls board_get(board, -1) at the recursion base case"""
    board = (0, 1, 2, 3, 4, 5, 6, 7)
    below = board_get(board, -1)
    at_end = board_get(board, N)
    well_above = board_get(board, N + 5)
    if below == -1 and at_end == -1 and well_above == -1:
        print("Test case 2 passed")
    else:
        print("Test case 2 failed")
    print("Expected -1 for all out-of-range indices and found", below, at_end, well_above, "\n")

def test_case_3():
    """A queen at (0,0) attacks another queen sharing its column (0,0) or lying on a diagonal (2,2), but not one safely placed elsewhere (1,3)"""
    same_column = safety_test1(0, 0, 0, 0)
    same_diagonal = safety_test1(0, 0, 2, 2)
    no_attack = safety_test1(0, 0, 1, 3)
    if same_column is False and same_diagonal is False and no_attack is True:
        print("Test case 3 passed")
    else:
        print("Test case 3 failed")
    print("Expected [False, False, True] and found", [same_column, same_diagonal, no_attack], "\n")


##########################################################################
# Run test cases
##########################################################################

test_case_1()
test_case_2()
test_case_3()