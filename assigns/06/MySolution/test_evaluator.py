"""
Shared source and target evaluation:
RED-01 through RED-05, CMP-04, CMP-08, QLT-02,
ACC-02 through ACC-04, ACC-07

Run from assigns/06:
python3 -m unittest discover -s MySolution -p 'test_*.py' -v

Source evaluation is unbounded, so divergent examples are tested only through the bounded target evaluator
"""

import unittest
from copy import deepcopy

import lambda1_vp as source

from target import Var, Lam, App
from evaluator import (
    stepTarget,
    evaluateTarget,
    evaluate,
    lookupSource,
)


def identity():
    return Lam("x", Var("x"))


def constant():
    return Lam("a", Lam("b", Var("a")))


def omega():
    function = Lam("x", App(Var("x"), Var("x")))
    return App(function, function)


class TestStepTarget(unittest.TestCase):
    def test_beta_value_contraction(self):
        self.assertEqual(
            stepTarget(App(identity(), constant())),
            constant(),
        )

    def test_reduces_function_before_argument(self):
        term = App(
            App(identity(), constant()),
            App(identity(), identity()),
        )

        expected = App(
            constant(),
            App(identity(), identity()),
        )

        self.assertEqual(stepTarget(term), expected)

    def test_reduces_argument_when_function_is_value(self):
        term = App(
            constant(),
            App(identity(), identity()),
        )

        self.assertEqual(
            stepTarget(term),
            App(constant(), identity()),
        )

    def test_performs_only_one_contraction(self):
        term = App(
            App(identity(), identity()),
            constant(),
        )

        self.assertEqual(
            stepTarget(term),
            App(identity(), constant()),
        )

    def test_preserves_input(self):
        term = App(identity(), constant())
        snapshot = deepcopy(term)

        stepTarget(term)

        self.assertEqual(term, snapshot)

    def test_rejects_free_variable(self):
        with self.assertRaises(ValueError):
            stepTarget(Var("free"))

    def test_rejects_lambda_and_unsupported_node(self):
        for term in [identity(), object()]:
            with self.subTest(term=term):
                with self.assertRaises(TypeError):
                    stepTarget(term)


class TestEvaluateTarget(unittest.TestCase):
    def test_budget_boundaries(self):
        cases = [
            (identity(), 0, "completed", identity(), 0),
            (
                App(identity(), constant()),
                0,
                "exhausted",
                App(identity(), constant()),
                0,
            ),
            (
                App(identity(), constant()),
                1,
                "completed",
                constant(),
                1,
            ),
            (
                App(App(identity(), identity()), constant()),
                1,
                "exhausted",
                App(identity(), constant()),
                1,
            ),
            (
                App(App(identity(), identity()), constant()),
                2,
                "completed",
                constant(),
                2,
            ),
        ]

        for term, budget, status, expected, steps in cases:
            with self.subTest(term=term, budget=budget):
                result = evaluateTarget(term, budget)

                self.assertEqual(result.status, status)
                self.assertEqual(result.term, expected)
                self.assertEqual(result.steps, steps)

    def test_does_not_reduce_under_lambda(self):
        term = Lam(
            "x",
            App(Lam("y", Var("y")), Var("x")),
        )

        result = evaluateTarget(term, 10)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.term, term)
        self.assertEqual(result.steps, 0)

    def test_does_not_eta_reduce(self):
        term = Lam(
            "x",
            App(identity(), Var("x")),
        )

        result = evaluateTarget(term, 10)

        self.assertEqual(result.term, term)
        self.assertEqual(result.steps, 0)

    def test_divergence_exhausts_budget(self):
        for budget in [0, 1, 5, 20]:
            with self.subTest(budget=budget):
                result = evaluateTarget(omega(), budget)

                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.term, omega())
                self.assertEqual(result.steps, budget)

    def test_unused_argument_is_still_evaluated(self):
        term = App(
            Lam("unused", identity()),
            omega(),
        )

        result = evaluateTarget(term, 5)

        self.assertEqual(result.status, "exhausted")
        self.assertEqual(result.steps, 5)

    def test_determinism_and_input_preservation(self):
        term = App(App(identity(), identity()), constant())
        snapshot = deepcopy(term)

        first = evaluateTarget(term, 10)
        second = evaluateTarget(term, 10)

        self.assertEqual(first, second)
        self.assertEqual(term, snapshot)

    def test_rejects_invalid_budgets(self):
        for budget in [-1, 1.5, "3", None, True, False]:
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    evaluateTarget(identity(), budget)

    def test_rejects_open_terms_even_with_zero_budget(self):
        for term in [
            Var("free"),
            Lam("x", Var("free")),
            App(identity(), Var("free")),
        ]:
            with self.subTest(term=term):
                with self.assertRaises(ValueError):
                    evaluateTarget(term, 0)

    def test_rejects_malformed_terms_before_execution(self):
        for term in [
            object(),
            Lam("", Var("x")),
            Lam("x", 42),
            App(identity(), 42),
        ]:
            with self.subTest(term=term):
                with self.assertRaises((TypeError, ValueError)):
                    evaluateTarget(term, 0)


class TestLookupSource(unittest.TestCase):
    def test_finds_binding(self):
        environment = source.ENVcns(
            "x",
            source.D0Vint(3),
            source.ENVnil(),
        )

        self.assertEqual(
            lookupSource(environment, "x"),
            source.D0Vint(3),
        )

    def test_nearest_binding_shadows_older_binding(self):
        older = source.ENVcns(
            "x",
            source.D0Vint(3),
            source.ENVnil(),
        )
        newer = source.ENVcns(
            "x",
            source.D0Vint(7),
            older,
        )

        self.assertEqual(lookupSource(newer, "x"), source.D0Vint(7))
        self.assertEqual(lookupSource(older, "x"), source.D0Vint(3))

    def test_searches_older_bindings(self):
        environment = source.ENVcns(
            "y",
            source.D0Vbtf(True),
            source.ENVcns(
                "x",
                source.D0Vint(3),
                source.ENVnil(),
            ),
        )

        self.assertEqual(
            lookupSource(environment, "x"),
            source.D0Vint(3),
        )

    def test_rejects_unbound_variable(self):
        with self.assertRaises(ValueError):
            lookupSource(source.ENVnil(), "missing")


class TestSourceEvaluation(unittest.TestCase):
    def test_literals(self):
        cases = [
            (source.D0Eint(0), source.D0Vint(0)),
            (source.D0Eint(5), source.D0Vint(5)),
            (source.D0Ebtf(True), source.D0Vbtf(True)),
            (source.D0Ebtf(False), source.D0Vbtf(False)),
        ]

        for expression, expected in cases:
            with self.subTest(expression=expression):
                self.assertEqual(evaluate(expression), expected)

    def test_arithmetic(self):
        cases = [
            ("+", 2, 3, 5),
            ("*", 3, 4, 12),
            ("*", 0, 4, 0),
            ("-", 5, 2, 3),
            ("-", 2, 5, 0),
            ("-", 3, 3, 0),
        ]

        for operator, left, right, expected in cases:
            with self.subTest(operator=operator, left=left, right=right):
                expression = source.D0Eop2(
                    operator,
                    source.D0Eint(left),
                    source.D0Eint(right),
                )

                self.assertEqual(
                    evaluate(expression),
                    source.D0Vint(expected),
                )

    def test_all_comparisons(self):
        cases = [
            ("<", [True, False, False]),
            ("<=", [True, True, False]),
            (">", [False, False, True]),
            (">=", [False, True, True]),
            ("==", [False, True, False]),
            ("!=", [True, False, True]),
        ]
        operands = [(2, 3), (3, 3), (4, 3)]

        for operator, expected_results in cases:
            for (left, right), expected in zip(operands, expected_results):
                with self.subTest(
                    operator=operator,
                    left=left,
                    right=right,
                ):
                    expression = source.D0Eop2(
                        operator,
                        source.D0Eint(left),
                        source.D0Eint(right),
                    )

                    self.assertEqual(
                        evaluate(expression),
                        source.D0Vbtf(expected),
                    )

    def test_not(self):
        for value, expected in [(True, False), (False, True)]:
            with self.subTest(value=value):
                expression = source.D0Eop1(
                    "not",
                    source.D0Ebtf(value),
                )

                self.assertEqual(
                    evaluate(expression),
                    source.D0Vbtf(expected),
                )

    def test_boolean_truth_tables(self):
        cases = [
            ("and", False, False, False),
            ("and", False, True, False),
            ("and", True, False, False),
            ("and", True, True, True),
            ("or", False, False, False),
            ("or", False, True, True),
            ("or", True, False, True),
            ("or", True, True, True),
        ]

        for operator, left, right, expected in cases:
            with self.subTest(operator=operator, left=left, right=right):
                expression = source.D0Eop2(
                    operator,
                    source.D0Ebtf(left),
                    source.D0Ebtf(right),
                )

                self.assertEqual(
                    evaluate(expression),
                    source.D0Vbtf(expected),
                )

    def test_boolean_short_circuit(self):
        # An unbound variable reveals whether the right operand runs.
        cases = [
            ("and", False, False),
            ("or", True, True),
        ]

        for operator, left, expected in cases:
            with self.subTest(operator=operator):
                expression = source.D0Eop2(
                    operator,
                    source.D0Ebtf(left),
                    source.D0Evar("must_not_run"),
                )

                self.assertEqual(
                    evaluate(expression),
                    source.D0Vbtf(expected),
                )

    def test_boolean_right_operand_runs_when_required(self):
        for operator, left in [("and", True), ("or", False)]:
            with self.subTest(operator=operator):
                expression = source.D0Eop2(
                    operator,
                    source.D0Ebtf(left),
                    source.D0Evar("must_run"),
                )

                with self.assertRaises(ValueError):
                    evaluate(expression)

    def test_conditional_evaluates_only_selected_branch(self):
        cases = [
            (
                True,
                source.D0Eint(7),
                source.D0Evar("must_not_run"),
                7,
            ),
            (
                False,
                source.D0Evar("must_not_run"),
                source.D0Eint(9),
                9,
            ),
        ]

        for condition, true_branch, false_branch, expected in cases:
            with self.subTest(condition=condition):
                expression = source.D0Eif0(
                    source.D0Ebtf(condition),
                    true_branch,
                    false_branch,
                )

                self.assertEqual(
                    evaluate(expression),
                    source.D0Vint(expected),
                )

    def test_lambda_application(self):
        expression = source.D0Eapp(
            source.D0Elam("x", source.D0Evar("x")),
            source.D0Eint(4),
        )

        self.assertEqual(evaluate(expression), source.D0Vint(4))

    def test_lambda_body_is_delayed(self):
        expression = source.D0Elam(
            "x",
            source.D0Evar("must_not_run"),
        )

        self.assertIsInstance(evaluate(expression), source.D0Vlam)

    def test_lexical_scope_uses_defining_environment(self):
        # let x = 3 in
        # let f = (lam y. x + y) in
        # let x = 100 in f 4
        expression = source.D0Elet(
            "x",
            source.D0Eint(3),
            source.D0Elet(
                "f",
                source.D0Elam(
                    "y",
                    source.D0Eop2(
                        "+",
                        source.D0Evar("x"),
                        source.D0Evar("y"),
                    ),
                ),
                source.D0Elet(
                    "x",
                    source.D0Eint(100),
                    source.D0Eapp(
                        source.D0Evar("f"),
                        source.D0Eint(4),
                    ),
                ),
            ),
        )

        self.assertEqual(evaluate(expression), source.D0Vint(7))

    def test_let_initializer_uses_outer_binding(self):
        # let x = 3 in let x = x + 1 in x
        expression = source.D0Elet(
            "x",
            source.D0Eint(3),
            source.D0Elet(
                "x",
                source.D0Eop2(
                    "+",
                    source.D0Evar("x"),
                    source.D0Eint(1),
                ),
                source.D0Evar("x"),
            ),
        )

        self.assertEqual(evaluate(expression), source.D0Vint(4))

    def test_lambda_parameter_shadows_outer_binding(self):
        expression = source.D0Elet(
            "x",
            source.D0Eint(3),
            source.D0Eapp(
                source.D0Elam("x", source.D0Evar("x")),
                source.D0Eint(7),
            ),
        )

        self.assertEqual(evaluate(expression), source.D0Vint(7))

    def test_nested_pair_and_projections(self):
        expression = source.D0Epair(
            source.D0Epair(
                source.D0Eint(2),
                source.D0Ebtf(True),
            ),
            source.D0Eint(3),
        )

        expected = source.D0Vpair(
            source.D0Vpair(
                source.D0Vint(2),
                source.D0Vbtf(True),
            ),
            source.D0Vint(3),
        )

        self.assertEqual(evaluate(expression), expected)
        self.assertEqual(
            evaluate(source.D0Epfst(source.D0Epfst(expression))),
            source.D0Vint(2),
        )
        self.assertEqual(
            evaluate(source.D0Epsnd(source.D0Epfst(expression))),
            source.D0Vbtf(True),
        )
        self.assertEqual(
            evaluate(source.D0Epsnd(expression)),
            source.D0Vint(3),
        )

    def test_unused_arguments_and_initializers_are_strict(self):
        cases = [
            source.D0Eapp(
                source.D0Elam("unused", source.D0Eint(0)),
                source.D0Evar("missing"),
            ),
            source.D0Elet(
                "unused",
                source.D0Evar("missing"),
                source.D0Eint(0),
            ),
        ]

        for expression in cases:
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    evaluate(expression)

    def test_projection_still_evaluates_both_pair_components(self):
        cases = [
            source.D0Epfst(
                source.D0Epair(
                    source.D0Eint(2),
                    source.D0Evar("missing"),
                ),
            ),
            source.D0Epsnd(
                source.D0Epair(
                    source.D0Evar("missing"),
                    source.D0Ebtf(True),
                ),
            ),
        ]

        for expression in cases:
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    evaluate(expression)

    def test_left_to_right_evaluation_order(self):
        # Distinct missing names reveal which operand runs first.
        cases = [
            source.D0Eapp(
                source.D0Evar("left"),
                source.D0Evar("right"),
            ),
            source.D0Eop2(
                "+",
                source.D0Evar("left"),
                source.D0Evar("right"),
            ),
            source.D0Epair(
                source.D0Evar("left"),
                source.D0Evar("right"),
            ),
        ]

        for expression in cases:
            with self.subTest(expression=expression):
                with self.assertRaisesRegex(ValueError, "left"):
                    evaluate(expression)

    def test_rejects_unbound_variable(self):
        with self.assertRaises(ValueError):
            evaluate(source.D0Evar("missing"))

    def test_rejects_negative_literal_and_unsupported_operators(self):
        cases = [
            source.D0Eint(-1),
            source.D0Eop1("+1", source.D0Eint(2)),
            source.D0Eop2("/", source.D0Eint(4), source.D0Eint(2)),
        ]

        for expression in cases:
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    evaluate(expression)

    def test_preserves_source_ast(self):
        expression = source.D0Elet(
            "x",
            source.D0Eint(3),
            source.D0Eop2(
                "+",
                source.D0Evar("x"),
                source.D0Eint(4),
            ),
        )
        snapshot = deepcopy(expression)

        first = evaluate(expression)
        second = evaluate(expression)

        self.assertEqual(first, source.D0Vint(7))
        self.assertEqual(first, second)
        self.assertEqual(expression, snapshot)


class TestSourceRecursion(unittest.TestCase):
    def test_fix_definition_is_delayed(self):
        expression = source.D0Efix(
            "f",
            "x",
            source.D0Evar("must_not_run"),
        )

        self.assertIsInstance(evaluate(expression), source.D0Vfix)

    def test_coincident_fix_binders(self):
        # (fix f(f). f) 3
        expression = source.D0Eapp(
            source.D0Efix("f", "f", source.D0Evar("f")),
            source.D0Eint(3),
        )

        self.assertEqual(evaluate(expression), source.D0Vint(3))

    def test_factorial_of_four(self):
        # fix fact(n).
        #   if n == 0 then 1 else n * fact(n - 1)
        factorial = source.D0Efix(
            "fact",
            "n",
            source.D0Eif0(
                source.D0Eop2(
                    "==",
                    source.D0Evar("n"),
                    source.D0Eint(0),
                ),
                source.D0Eint(1),
                source.D0Eop2(
                    "*",
                    source.D0Evar("n"),
                    source.D0Eapp(
                        source.D0Evar("fact"),
                        source.D0Eop2(
                            "-",
                            source.D0Evar("n"),
                            source.D0Eint(1),
                        ),
                    ),
                ),
            ),
        )

        expression = source.D0Eapp(factorial, source.D0Eint(4))

        self.assertEqual(evaluate(expression), source.D0Vint(24))

    def test_fibonacci_of_five(self):
        # fix fib(n).
        #   if n <= 1 then n else fib(n - 1) + fib(n - 2)
        fibonacci = source.D0Efix(
            "fib",
            "n",
            source.D0Eif0(
                source.D0Eop2(
                    "<=",
                    source.D0Evar("n"),
                    source.D0Eint(1),
                ),
                source.D0Evar("n"),
                source.D0Eop2(
                    "+",
                    source.D0Eapp(
                        source.D0Evar("fib"),
                        source.D0Eop2(
                            "-",
                            source.D0Evar("n"),
                            source.D0Eint(1),
                        ),
                    ),
                    source.D0Eapp(
                        source.D0Evar("fib"),
                        source.D0Eop2(
                            "-",
                            source.D0Evar("n"),
                            source.D0Eint(2),
                        ),
                    ),
                ),
            ),
        )

        expression = source.D0Eapp(fibonacci, source.D0Eint(5))

        self.assertEqual(evaluate(expression), source.D0Vint(5))


class TestSharedEvaluate(unittest.TestCase):
    def test_dispatches_target_expression(self):
        result = evaluate(App(identity(), constant()), budget=1)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.term, constant())
        self.assertEqual(result.steps, 1)

    def test_dispatches_source_expression(self):
        self.assertEqual(
            evaluate(source.D0Eint(3)),
            source.D0Vint(3),
        )

    def test_target_requires_budget(self):
        with self.assertRaises(ValueError):
            evaluate(identity())

    def test_rejects_unsupported_objects(self):
        for expression in [42, True, None, "x", object()]:
            with self.subTest(expression=expression):
                with self.assertRaises(TypeError):
                    evaluate(expression)


if __name__ == "__main__":
    unittest.main()