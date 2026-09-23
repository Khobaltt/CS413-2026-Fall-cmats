"""Examples for pairs and projections (T0Mpair, T0Mpfst, T0Mpsnd).

Run with: python3 MySolution/TEST/test02_lambda0.py
Requires Python 3.12 or later, like lambda0.py.
"""

import sys
import unittest
from pathlib import Path

# Allow this file to run directly from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mbtf, T0Mstr, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mif0, T0Mop1, T0Mop2,
    T0Mpair, T0Mpfst, T0Mpsnd,
    t0erm_size, t0erm_fvset, t0erm_subst0, t0erm_cbv_evaluate0,
)

#######################################################################################################################
# 1. Sizes and free-variable sets of pairs, projections, and nested terms
#######################################################################################################################
class TestSize(unittest.TestCase):
    def test_simple_pair(self):
        # Given example: 1 (pair) + 1 (int) + 1 (int) = 3.
        self.assertEqual(t0erm_size(T0Mpair(T0Mint(1), T0Mint(2))), 3)

    def test_projections(self):
        self.assertEqual(t0erm_size(T0Mpfst(T0Mint(1))), 2)
        self.assertEqual(t0erm_size(T0Mpsnd(T0Mint(1))), 2)

    def test_nested_pairs(self):
        # ((1, 2), (3, 4)): 1 + 3 + 3 = 7.
        term = T0Mpair(
            T0Mpair(T0Mint(1), T0Mint(2)),
            T0Mpair(T0Mint(3), T0Mint(4)),
        )
        self.assertEqual(t0erm_size(term), 7)

    def test_projection_of_pair(self):
        # fst((1, 2)): 1 (fst) + 1 (pair) + 1 + 1 = 4.
        term = T0Mpfst(T0Mpair(T0Mint(1), T0Mint(2)))
        self.assertEqual(t0erm_size(term), 4)

    def test_pair_inside_other_constructs(self):
        # if true then fst(1, 2) else 0: 1 + 1 + 4 + 1 = 7.
        term = T0Mif0(T0Mbtf(True), T0Mpfst(T0Mpair(T0Mint(1), T0Mint(2))), T0Mint(0))
        self.assertEqual(t0erm_size(term), 7)


class TestFvset(unittest.TestCase):
    def test_pfst_pair(self):
        # Given example.
        term = T0Mpfst(T0Mpair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))

    def test_psnd_pair(self):
        term = T0Mpsnd(T0Mpair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))

    def test_pair_no_binding(self):
        # Pairs/projections bind nothing, so repeated variables just union.
        term = T0Mpair(T0Mvar("a"), T0Mvar("a"))
        self.assertEqual(t0erm_fvset(term), frozenset({"a"}))

    def test_nested_pairs(self):
        term = T0Mpair(
            T0Mpair(T0Mvar("a"), T0Mvar("b")),
            T0Mpfst(T0Mvar("c")),
        )
        self.assertEqual(t0erm_fvset(term), frozenset({"a", "b", "c"}))

    def test_pair_under_lambda_binds_component(self):
        # lambda x. (x, y): x is bound, y stays free.
        term = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_fvset(term), frozenset({"y"}))

    def test_projection_no_free_vars(self):
        term = T0Mpfst(T0Mpair(T0Mint(1), T0Mint(2)))
        self.assertEqual(t0erm_fvset(term), frozenset())

#######################################################################################################################
# 2. Substitution into both pair components and projection operands, including under lambda or recursive-function binders
#######################################################################################################################
class TestSubst(unittest.TestCase):
    def test_into_pair_both_components(self):
        term = T0Mpair(T0Mvar("x"), T0Mvar("y"))
        result = t0erm_subst0(term, "x", T0Mint(99))
        self.assertEqual(result, T0Mpair(T0Mint(99), T0Mvar("y")))

    def test_into_projection_operand(self):
        term = T0Mpfst(T0Mpair(T0Mvar("x"), T0Mvar("y")))
        result = t0erm_subst0(term, "x", T0Mint(99))
        self.assertEqual(result, T0Mpfst(T0Mpair(T0Mint(99), T0Mvar("y"))))

    def test_both_sides_same_variable(self):
        term = T0Mpair(T0Mvar("x"), T0Mvar("x"))
        result = t0erm_subst0(term, "x", T0Mint(7))
        self.assertEqual(result, T0Mpair(T0Mint(7), T0Mint(7)))

    def test_under_lambda_shadowed(self):
        # lambda x. (x, y): substituting for x must not touch the bound x.
        term = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        result = t0erm_subst0(term, "x", T0Mint(99))
        self.assertEqual(result, term)

    def test_under_lambda_reaches_free_variable(self):
        # lambda x. (x, y): substituting for free y should reach inside the pair.
        term = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        result = t0erm_subst0(term, "y", T0Mint(42))
        self.assertEqual(result, T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mint(42))))

    def test_under_fix_shadowed(self):
        # fix f(x) = (f, x): both f and x are bound by the fix.
        term = T0Mfix("f", "x", T0Mpair(T0Mvar("f"), T0Mvar("x")))
        self.assertEqual(t0erm_subst0(term, "f", T0Mint(1)), term)
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(2)), term)

    def test_under_fix_reaches_free_variable(self):
        # fix f(x) = (f, y): y is free.
        term = T0Mfix("f", "x", T0Mpair(T0Mvar("f"), T0Mvar("y")))
        result = t0erm_subst0(term, "y", T0Mint(5))
        self.assertEqual(result, T0Mfix("f", "x", T0Mpair(T0Mvar("f"), T0Mint(5))))

    def test_nested_pairs(self):
        term = T0Mpair(T0Mpair(T0Mvar("x"), T0Mint(0)), T0Mvar("x"))
        result = t0erm_subst0(term, "x", T0Mint(3))
        self.assertEqual(result, T0Mpair(T0Mpair(T0Mint(3), T0Mint(0)), T0Mint(3)))

#######################################################################################################################
# 3. Pair construction with components that require evaluation, and both projections of the resulting pair
#######################################################################################################################
class TestCBVEvaluatePairs(unittest.TestCase):
    def test_given_example(self):
        term = T0Mpsnd(T0Mpair(T0Mint(1), T0Mop2("+", T0Mint(2), T0Mint(3))))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(5))

    def test_pair_requires_evaluation_both_sides(self):
        term = T0Mpair(
            T0Mop2("+", T0Mint(1), T0Mint(1)),
            T0Mop2("*", T0Mint(3), T0Mint(3)),
        )
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mpair(T0Mint(2), T0Mint(9)))

    def test_fst_of_computed_pair(self):
        term = T0Mpfst(T0Mpair(
            T0Mop2("+", T0Mint(1), T0Mint(1)),
            T0Mop2("*", T0Mint(3), T0Mint(3)),
        ))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(2))

    def test_snd_of_computed_pair(self):
        term = T0Mpsnd(T0Mpair(
            T0Mop2("+", T0Mint(1), T0Mint(1)),
            T0Mop2("*", T0Mint(3), T0Mint(3)),
        ))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(9))

    ###################################################################################################################
    # 4. Pair construction with components that require evaluation, and both projections of the resulting pair
    ###################################################################################################################
    def test_nested_pairs(self):
        term = T0Mpair(
            T0Mpair(T0Mint(1), T0Mint(2)),
            T0Mpair(T0Mint(3), T0Mint(4)),
        )
        expected = T0Mpair(T0Mpair(T0Mint(1), T0Mint(2)), T0Mpair(T0Mint(3), T0Mint(4)))
        self.assertEqual(t0erm_cbv_evaluate0(term), expected)

    def test_nested_pair_projection(self):
        # fst(snd(((1, 2), (3, 4)))) == 3.
        term = T0Mpfst(T0Mpsnd(T0Mpair(
            T0Mpair(T0Mint(1), T0Mint(2)),
            T0Mpair(T0Mint(3), T0Mint(4)),
        )))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(3))

    def test_pair_mixed_value_kinds(self):
        # A pair containing an int and a function.
        term = T0Mpair(T0Mint(1), T0Mlam("x", T0Mvar("x")))
        expected = T0Mpair(T0Mint(1), T0Mlam("x", T0Mvar("x")))
        self.assertEqual(t0erm_cbv_evaluate0(term), expected)

    def test_pair_containing_bool_and_str(self):
        term = T0Mpair(T0Mbtf(True), T0Mstr("hello"))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mpair(T0Mbtf(True), T0Mstr("hello")))

    ###################################################################################################################
    # 5. Functions that accept or return pairs, exercising substitution during application
    ###################################################################################################################
    def test_function_accepts_pair(self):
        # (lambda p. fst(p) + snd(p)) applied to (2, 3) == 5.
        func = T0Mlam("p", T0Mop2("+", T0Mpfst(T0Mvar("p")), T0Mpsnd(T0Mvar("p"))))
        term = T0Mapp(func, T0Mpair(T0Mint(2), T0Mint(3)))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(5))

    def test_function_returns_pair(self):
        # (lambda x. (x, x + 1)) applied to 4 == (4, 5).
        func = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mop2("+", T0Mvar("x"), T0Mint(1))))
        term = T0Mapp(func, T0Mint(4))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mpair(T0Mint(4), T0Mint(5)))

    def test_function_swaps_pair(self):
        # (lambda p. (snd(p), fst(p))) applied to (1, 2) == (2, 1).
        func = T0Mlam("p", T0Mpair(T0Mpsnd(T0Mvar("p")), T0Mpfst(T0Mvar("p"))))
        term = T0Mapp(func, T0Mpair(T0Mint(1), T0Mint(2)))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mpair(T0Mint(2), T0Mint(1)))

    def test_recursive_function_over_pair(self):
        # fix f(p) = if fst(p) == 0 then snd(p)
        #            else f((fst(p) - 1, snd(p) + fst(p)))
        # Sums 1..fst(p) into snd(p); starting from (3, 0) gives 6.
        # Exercises t0erm_subst0 for pairs occurring under a fix binder.
        body = T0Mif0(
            T0Mop2("==", T0Mpfst(T0Mvar("p")), T0Mint(0)),
            T0Mpsnd(T0Mvar("p")),
            T0Mapp(
                T0Mvar("f"),
                T0Mpair(
                    T0Mop2("-", T0Mpfst(T0Mvar("p")), T0Mint(1)),
                    T0Mop2("+", T0Mpsnd(T0Mvar("p")), T0Mpfst(T0Mvar("p"))),
                ),
            ),
        )
        function = T0Mfix("f", "p", body)
        term = T0Mapp(function, T0Mpair(T0Mint(3), T0Mint(0)))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(6))

    ###################################################################################################################
    # 6. A projection applied to a non-pair value, which must raise TypeError
    ###################################################################################################################
    def test_fst_of_non_pair_raises(self):
        with self.assertRaises(TypeError):
            t0erm_cbv_evaluate0(T0Mpfst(T0Mint(5)))

    def test_snd_of_non_pair_raises(self):
        with self.assertRaises(TypeError):
            t0erm_cbv_evaluate0(T0Mpsnd(T0Mint(5)))

    def test_fst_of_function_raises(self):
        with self.assertRaises(TypeError):
            t0erm_cbv_evaluate0(T0Mpfst(T0Mlam("x", T0Mvar("x"))))

    ###################################################################################################################
    # 7. Left-to-right evaluation of pair components, and evaluation of the component that a projection does not select
    ###################################################################################################################
    def test_pair_both_sides_evaluated_fst_selected(self):
        # Given example: fst((1, 1/0)) must raise ZeroDivisionError,
        # not silently return 1.
        term = T0Mpfst(T0Mpair(T0Mint(1), T0Mop2("/", T0Mint(1), T0Mint(0))))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_pair_both_sides_evaluated_snd_selected(self):
        # Symmetric case: snd((1/0, 2)) must also raise, even though
        # arg1 (the divide-by-zero) is the component NOT being projected.
        term = T0Mpsnd(T0Mpair(T0Mop2("/", T0Mint(1), T0Mint(0)), T0Mint(2)))
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

    def test_pair_left_to_right_order(self):
        # arg1 raises ZeroDivisionError; arg2 would raise TypeError instead.
        # If evaluation is left-to-right, arg1's error must propagate,
        # since arg2 should never be reached.
        term = T0Mpair(
            T0Mop2("/", T0Mint(1), T0Mint(0)),   # raises ZeroDivisionError
            T0Mapp(T0Mint(5), T0Mint(1)),         # would raise TypeError
        )
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(term)

#######################################################################################################################
# Other general safety checks
#######################################################################################################################
class TestExistingBehaviorStillWorks(unittest.TestCase):
    """Re-run a sample of the pre-extension behavior against the
    extended implementation, to confirm the pair/projection additions
    didn't disturb anything else."""

    def test_size(self):
        self.assertEqual(t0erm_size(T0Mint(1)), 1)
        self.assertEqual(t0erm_size(T0Mvar("x")), 1)
        self.assertEqual(t0erm_size(T0Mlam("x", T0Mvar("x"))), 2)
        self.assertEqual(t0erm_size(T0Mapp(T0Mvar("f"), T0Mvar("x"))), 3)

    def test_fvset(self):
        self.assertEqual(t0erm_fvset(T0Mlam("x", T0Mvar("x"))), frozenset())
        self.assertEqual(t0erm_fvset(T0Mlam("x", T0Mvar("y"))), frozenset({"y"}))
        self.assertEqual(t0erm_fvset(T0Mapp(T0Mvar("f"), T0Mvar("x"))), frozenset({"f", "x"}))

    def test_subst(self):
        term = T0Mapp(T0Mvar("f"), T0Mvar("x"))
        result = t0erm_subst0(term, "x", T0Mint(1))
        self.assertEqual(result, T0Mapp(T0Mvar("f"), T0Mint(1)))

    def test_eval(self):
        term = T0Mapp(T0Mlam("x", T0Mop2("+", T0Mvar("x"), T0Mint(1))), T0Mint(4))
        self.assertEqual(t0erm_cbv_evaluate0(term), T0Mint(5))

        fact = T0Mfix("f", "n", T0Mif0(
            T0Mop2("==", T0Mvar("n"), T0Mint(0)),
            T0Mint(1),
            T0Mop2("*", T0Mvar("n"), T0Mapp(T0Mvar("f"), T0Mop2("-", T0Mvar("n"), T0Mint(1)))),
        ))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mapp(fact, T0Mint(5))), T0Mint(120))


if __name__ == "__main__":
    unittest.main(verbosity=2)