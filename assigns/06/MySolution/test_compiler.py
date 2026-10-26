"""
Compilation, scope, delayed control flow, and recursion: CMP-01 through CMP-08

Run from assigns/06:
python3 -m unittest discover -s MySolution -p 'test_*.py' -v
"""

import unittest
from copy import deepcopy
from unittest.mock import patch

import lambda1_vp as source
import evaluator
import observers

from compiler import Compiler, compile_expr
from target import Var, Lam, App, validateTarget
from scope import freeVariables
from evaluator import evaluate
from observers import observe


def loopExpression():
    """Return a closed diverging source expression; never evaluate it as source"""
    return source.D0Eapp(
        source.D0Efix(
            "loop", "x",
            source.D0Eapp(source.D0Evar("loop"), source.D0Evar("x")),
        ),
        source.D0Eint(0),
    )


class CompilerTestCase(unittest.TestCase):
    """Shared assertions for source results and independently observed target results"""

    executionBudget = 100000
    observationBudget = 100000

    def assertSourceValue(self, value, kind, expected):
        # Check source value types as well as their contents
        if kind == "nat":
            self.assertIsInstance(value, source.D0Vint)
            self.assertEqual(value.arg1, expected)
        elif kind == "bool":
            self.assertIsInstance(value, source.D0Vbtf)
            self.assertIs(value.arg1, expected)
        else:
            self.assertIsInstance(value, source.D0Vpair)
            self.assertSourceValue(value.arg1, kind[1], expected[0])
            self.assertSourceValue(value.arg2, kind[2], expected[1])

    def assertCompiledValue(self, expression, kind, expected):
        term = compile_expr(expression)
        self.assertIsNone(validateTarget(term))
        self.assertEqual(freeVariables(term), set(source.d0exp_fvset(expression)))

        # Program execution and observation have separate budgets and counts
        execution = evaluate(term, budget=self.executionBudget)
        self.assertEqual(execution.status, "completed")
        observation = observe(execution.term, kind, budget=self.observationBudget)
        self.assertEqual(observation.status, "completed", observation.message)
        self.assertEqual(observation.value, expected)
        self.assertSourceValue(evaluate(expression), kind, expected)

    def assertCompiledExhausted(self, expression):
        # Source execution has no divergence budget, so use only the target path
        term = compile_expr(expression)
        self.assertIsNone(validateTarget(term))
        execution = evaluate(term, budget=100)
        self.assertEqual(execution.status, "exhausted")
        self.assertEqual(execution.steps, 100)


class TestCompilerVisitor(unittest.TestCase):
    def test_implements_source_visitor(self):
        self.assertIsInstance(Compiler(), source.D0ExpVisitor)

    def test_variable_lambda_and_application_structure(self):
        cases = [
            (source.D0Evar("free"), Var("free")),
            (source.D0Elam("x", source.D0Evar("x")), Lam("x", Var("x"))),
            (source.D0Eapp(source.D0Evar("f"), source.D0Evar("x")),
             App(Var("f"), Var("x"))),
            (source.D0Elet("x", source.D0Evar("a"), source.D0Evar("x")),
             App(Lam("x", Var("x")), Var("a"))),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                self.assertEqual(compile_expr(expression), expected)

    def test_compilation_does_not_evaluate_or_observe(self):
        # Patch both defining modules and possible compiler-local import aliases
        def forbidden(*args, **kwargs):
            self.fail("Compilation called evaluation or observation")

        expressions = [
            source.D0Eop2("+", source.D0Eint(2), source.D0Eint(3)),
            source.D0Eif0(source.D0Ebtf(True), source.D0Eint(1), loopExpression()),
            source.D0Efix("f", "x", source.D0Eapp(source.D0Evar("f"), source.D0Evar("x"))),
            loopExpression(),
        ]
        with patch.object(evaluator, "evaluate", side_effect=forbidden), \
             patch.object(evaluator, "evaluateTarget", side_effect=forbidden), \
             patch.object(source, "d0exp_evaluate", side_effect=forbidden), \
             patch.object(observers, "observe", side_effect=forbidden), \
             patch("compiler.evaluate", side_effect=forbidden, create=True), \
             patch("compiler.evaluateTarget", side_effect=forbidden, create=True), \
             patch("compiler.d0exp_evaluate", side_effect=forbidden, create=True), \
             patch("compiler.observe", side_effect=forbidden, create=True):
            for expression in expressions:
                with self.subTest(expression=expression):
                    self.assertIsNone(validateTarget(compile_expr(expression)))

    def test_input_immutability_and_deterministic_output(self):
        expression = source.D0Elet(
            "_thunk_0", source.D0Eint(3),
            source.D0Eif0(
                source.D0Ebtf(True),
                source.D0Evar("_thunk_0"),
                source.D0Eop2("+", source.D0Eint(1), source.D0Eint(2)),
            ),
        )
        snapshot = deepcopy(expression)
        first = compile_expr(expression)
        targetSnapshot = deepcopy(first)
        self.assertEqual(compile_expr(expression), first)
        self.assertEqual(expression, snapshot)
        evaluate(first, budget=1000)
        self.assertEqual(first, targetSnapshot)
        self.assertEqual(expression, snapshot)


class TestCompilerValues(CompilerTestCase):
    def test_natural_literals(self):
        for number in [0, 1, 2, 5]:
            with self.subTest(number=number):
                self.assertCompiledValue(source.D0Eint(number), "nat", number)

    def test_boolean_literals(self):
        for boolean in [True, False]:
            with self.subTest(boolean=boolean):
                self.assertCompiledValue(source.D0Ebtf(boolean), "bool", boolean)

    def test_lambda_application(self):
        self.assertCompiledValue(
            source.D0Eapp(source.D0Elam("x", source.D0Evar("x")), source.D0Eint(4)),
            "nat", 4,
        )

    def test_higher_order_application(self):
        expression = source.D0Eapp(
            source.D0Elam("f", source.D0Eapp(source.D0Evar("f"), source.D0Eint(3))),
            source.D0Elam("x", source.D0Eop2("+", source.D0Evar("x"), source.D0Eint(1))),
        )
        self.assertCompiledValue(expression, "nat", 4)

    def test_let_and_lexical_scope(self):
        expression = source.D0Elet(
            "x", source.D0Eint(3),
            source.D0Elet(
                "f", source.D0Elam("unused", source.D0Evar("x")),
                source.D0Elet(
                    "x", source.D0Eint(8),
                    source.D0Eapp(source.D0Evar("f"), source.D0Eint(0)),
                ),
            ),
        )
        self.assertCompiledValue(expression, "nat", 3)

    def test_shadowed_let_initializer_uses_outer_binding(self):
        expression = source.D0Elet(
            "x", source.D0Eint(2),
            source.D0Elet(
                "x", source.D0Eop2("+", source.D0Evar("x"), source.D0Eint(1)),
                source.D0Evar("x"),
            ),
        )
        self.assertCompiledValue(expression, "nat", 3)

    def test_pair_and_both_projections(self):
        pair = source.D0Epair(source.D0Eint(2), source.D0Ebtf(True))
        self.assertCompiledValue(pair, ("pair", "nat", "bool"), (2, True))
        self.assertCompiledValue(source.D0Epfst(pair), "nat", 2)
        self.assertCompiledValue(source.D0Epsnd(pair), "bool", True)

    def test_nested_pair(self):
        expression = source.D0Epair(
            source.D0Eint(2), source.D0Epair(source.D0Ebtf(False), source.D0Eint(3)),
        )
        self.assertCompiledValue(
            expression, ("pair", "nat", ("pair", "bool", "nat")), (2, (False, 3)),
        )


class TestCompilerOperators(CompilerTestCase):
    def test_arithmetic_boundaries(self):
        cases = [
            ("+", 0, 0, 0), ("+", 0, 3, 3), ("+", 2, 3, 5),
            ("-", 0, 0, 0), ("-", 0, 3, 0), ("-", 3, 0, 3),
            ("-", 2, 3, 0), ("-", 3, 2, 1), ("-", 3, 3, 0),
            ("*", 0, 3, 0), ("*", 3, 0, 0), ("*", 2, 3, 6),
        ]
        for operator, left, right, expected in cases:
            with self.subTest(operator=operator, left=left, right=right):
                expression = source.D0Eop2(operator, source.D0Eint(left), source.D0Eint(right))
                self.assertCompiledValue(expression, "nat", expected)

    def test_all_comparisons(self):
        # Expected answers are explicit and independent of the source evaluator
        cases = [
            (0, 0, [False, True, False, True, True, False]),
            (0, 2, [True, True, False, False, False, True]),
            (2, 0, [False, False, True, True, False, True]),
            (2, 2, [False, True, False, True, True, False]),
            (2, 3, [True, True, False, False, False, True]),
            (3, 2, [False, False, True, True, False, True]),
        ]
        for left, right, answers in cases:
            for operator, expected in zip(["<", "<=", ">", ">=", "==", "!="], answers):
                with self.subTest(operator=operator, left=left, right=right):
                    expression = source.D0Eop2(operator, source.D0Eint(left), source.D0Eint(right))
                    self.assertCompiledValue(expression, "bool", expected)

    def test_not_truth_table(self):
        for operand, expected in [(True, False), (False, True)]:
            with self.subTest(operand=operand):
                self.assertCompiledValue(source.D0Eop1("not", source.D0Ebtf(operand)), "bool", expected)

    def test_and_or_truth_tables(self):
        for left, right, conjunction, disjunction in [
            (False, False, False, False), (False, True, False, True),
            (True, False, False, True), (True, True, True, True),
        ]:
            for operator, expected in [("and", conjunction), ("or", disjunction)]:
                with self.subTest(operator=operator, left=left, right=right):
                    expression = source.D0Eop2(operator, source.D0Ebtf(left), source.D0Ebtf(right))
                    self.assertCompiledValue(expression, "bool", expected)

    def test_nested_arithmetic(self):
        expression = source.D0Eop2(
            "+", source.D0Eint(2), source.D0Eop2("*", source.D0Eint(3), source.D0Eint(4)),
        )
        self.assertCompiledValue(expression, "nat", 14)


class TestCompilerControlFlow(CompilerTestCase):
    def test_conditional_selects_only_one_branch(self):
        cases = [
            (source.D0Eif0(source.D0Ebtf(True), source.D0Eint(1), loopExpression()), 1),
            (source.D0Eif0(source.D0Ebtf(False), loopExpression(), source.D0Eint(2)), 2),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                self.assertCompiledValue(expression, "nat", expected)

    def test_boolean_operators_skip_diverging_right_operand(self):
        for operator, left, expected in [("and", False, False), ("or", True, True)]:
            with self.subTest(operator=operator):
                expression = source.D0Eop2(operator, source.D0Ebtf(left), loopExpression())
                self.assertCompiledValue(expression, "bool", expected)

    def test_boolean_operators_force_needed_right_operand(self):
        for operator, left in [("and", True), ("or", False)]:
            with self.subTest(operator=operator):
                self.assertCompiledExhausted(
                    source.D0Eop2(operator, source.D0Ebtf(left), loopExpression())
                )

    def test_condition_and_left_boolean_operand_are_evaluated(self):
        expressions = [
            source.D0Eif0(loopExpression(), source.D0Eint(1), source.D0Eint(2)),
            source.D0Eop2("and", loopExpression(), source.D0Ebtf(False)),
            source.D0Eop2("or", loopExpression(), source.D0Ebtf(True)),
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                self.assertCompiledExhausted(expression)

    def test_nested_conditionals(self):
        expression = source.D0Eif0(
            source.D0Eop2("<", source.D0Eint(1), source.D0Eint(2)),
            source.D0Eif0(source.D0Ebtf(False), loopExpression(), source.D0Eint(7)),
            loopExpression(),
        )
        self.assertCompiledValue(expression, "nat", 7)

    def test_selected_diverging_branch_exhausts(self):
        self.assertCompiledExhausted(
            source.D0Eif0(source.D0Ebtf(True), loopExpression(), source.D0Eint(0))
        )


class TestCompilerStrictness(CompilerTestCase):
    def test_unused_application_argument_is_evaluated(self):
        self.assertCompiledExhausted(
            source.D0Eapp(source.D0Elam("unused", source.D0Eint(1)), loopExpression())
        )

    def test_application_function_is_evaluated(self):
        self.assertCompiledExhausted(source.D0Eapp(loopExpression(), source.D0Eint(0)))

    def test_unused_let_initializer_is_evaluated(self):
        self.assertCompiledExhausted(source.D0Elet("unused", loopExpression(), source.D0Eint(1)))

    def test_both_pair_components_are_strict_even_under_projection(self):
        expressions = [
            source.D0Epfst(source.D0Epair(source.D0Eint(1), loopExpression())),
            source.D0Epsnd(source.D0Epair(loopExpression(), source.D0Eint(1))),
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                self.assertCompiledExhausted(expression)

    def test_multiplication_by_zero_still_evaluates_other_operand(self):
        for left, right in [(source.D0Eint(0), loopExpression()), (loopExpression(), source.D0Eint(0))]:
            with self.subTest(left=left, right=right):
                self.assertCompiledExhausted(source.D0Eop2("*", left, right))

    def test_lambda_body_is_delayed(self):
        term = compile_expr(source.D0Elam("unused", loopExpression()))
        result = evaluate(term, budget=0)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.steps, 0)
        self.assertIsInstance(result.term, Lam)


class TestCompilerScope(CompilerTestCase):
    def test_free_variable_preservation(self):
        expressions = [
            source.D0Evar("free"),
            source.D0Elam("x", source.D0Epair(source.D0Evar("x"), source.D0Evar("free"))),
            source.D0Elet("x", source.D0Evar("x"), source.D0Evar("x")),
            source.D0Eif0(source.D0Evar("c"), source.D0Evar("_thunk_0"), source.D0Evar("_thunk_1")),
            source.D0Eop2("and", source.D0Evar("p"), source.D0Evar("_thunk_0")),
            source.D0Eop2("or", source.D0Evar("p"), source.D0Evar("_thunk_1")),
            source.D0Efix("f", "x", source.D0Epair(source.D0Evar("f"), source.D0Evar("outside"))),
            source.D0Efix("f", "f", source.D0Epair(source.D0Evar("f"), source.D0Evar("outside"))),
        ]
        for expression in expressions:
            with self.subTest(expression=expression):
                self.assertEqual(freeVariables(compile_expr(expression)), set(source.d0exp_fvset(expression)))

    def test_thunk_and_encoding_name_collisions(self):
        for name in ["_thunk_0", "_thunk_1", "_thunk_2", "PLUS", "f", "x", "t", "s"]:
            with self.subTest(name=name):
                expression = source.D0Elet(
                    name, source.D0Eint(7),
                    source.D0Eif0(
                        source.D0Ebtf(True),
                        source.D0Eop2("+", source.D0Evar(name), source.D0Eint(1)),
                        loopExpression(),
                    ),
                )
                self.assertCompiledValue(expression, "nat", 8)

    def test_nested_lambda_shadowing(self):
        expression = source.D0Eapp(
            source.D0Eapp(
                source.D0Elam("x", source.D0Elam("x", source.D0Evar("x"))),
                source.D0Eint(1),
            ),
            source.D0Eint(2),
        )
        self.assertCompiledValue(expression, "nat", 2)

    def test_outer_binding_is_preserved_under_inner_lambda(self):
        expression = source.D0Eapp(
            source.D0Eapp(
                source.D0Elam("x", source.D0Elam("y", source.D0Evar("x"))),
                source.D0Eint(1),
            ),
            source.D0Eint(2),
        )
        self.assertCompiledValue(expression, "nat", 1)


class TestCompilerRecursion(CompilerTestCase):
    def test_fix_parameter_shadows_same_function_name(self):
        expression = source.D0Eapp(
            source.D0Efix("f", "f", source.D0Evar("f")), source.D0Eint(3),
        )
        self.assertCompiledValue(expression, "nat", 3)

    def test_fix_captures_outer_binding(self):
        expression = source.D0Elet(
            "outside", source.D0Eint(5),
            source.D0Eapp(source.D0Efix("f", "x", source.D0Evar("outside")), source.D0Eint(0)),
        )
        self.assertCompiledValue(expression, "nat", 5)

    def test_fix_body_is_delayed_until_application(self):
        term = compile_expr(source.D0Efix("f", "x", loopExpression()))
        result = evaluate(term, budget=100)
        self.assertEqual(result.status, "completed")
        self.assertIsInstance(result.term, Lam)

    def test_recursive_function_name_can_be_shadowed_by_let(self):
        expression = source.D0Eapp(
            source.D0Efix("f", "x", source.D0Elet("f", source.D0Eint(9), source.D0Evar("f"))),
            source.D0Eint(0),
        )
        self.assertCompiledValue(expression, "nat", 9)

    def test_factorial_four(self):
        n = source.D0Evar("n")
        factorial = source.D0Efix(
            "fact", "n",
            source.D0Eif0(
                source.D0Eop2("==", n, source.D0Eint(0)),
                source.D0Eint(1),
                source.D0Eop2(
                    "*", n,
                    source.D0Eapp(
                        source.D0Evar("fact"), source.D0Eop2("-", n, source.D0Eint(1)),
                    ),
                ),
            ),
        )
        self.assertCompiledValue(source.D0Eapp(factorial, source.D0Eint(4)), "nat", 24)

    def test_fibonacci_five(self):
        n = source.D0Evar("n")
        fibonacci = source.D0Efix(
            "fib", "n",
            source.D0Eif0(
                source.D0Eop2("<=", n, source.D0Eint(1)), n,
                source.D0Eop2(
                    "+",
                    source.D0Eapp(source.D0Evar("fib"), source.D0Eop2("-", n, source.D0Eint(1))),
                    source.D0Eapp(source.D0Evar("fib"), source.D0Eop2("-", n, source.D0Eint(2))),
                ),
            ),
        )
        self.assertCompiledValue(source.D0Eapp(fibonacci, source.D0Eint(5)), "nat", 5)

    def test_recursive_loop_exhausts(self):
        self.assertCompiledExhausted(loopExpression())

    def test_nonrecursive_self_application_loop_compiles(self):
        function = source.D0Elam("x", source.D0Eapp(source.D0Evar("x"), source.D0Evar("x")))
        self.assertCompiledExhausted(source.D0Eapp(function, function))


class TestCompilerValidation(unittest.TestCase):
    def test_invalid_literal_values(self):
        for expression in [source.D0Eint(-1), source.D0Eint(True), source.D0Eint(1.5),
                           source.D0Ebtf(0), source.D0Ebtf(1), source.D0Ebtf("true")]:
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    compile_expr(expression)

    def test_unsupported_operators(self):
        expressions = [source.D0Eop1(name, source.D0Eint(1)) for name in ["+1", "-1", "!", "unknown"]]
        expressions += [source.D0Eop2(name, source.D0Eint(1), source.D0Eint(2))
                        for name in ["/", "%", "**", "&&", "||", "unknown"]]
        for expression in expressions:
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    compile_expr(expression)

    def test_rejects_invalid_syntax_inside_delayed_code(self):
        for bad in [source.D0Eint(-1), source.D0Eop2("/", source.D0Eint(1), source.D0Eint(2))]:
            expressions = [
                source.D0Elam("x", bad),
                source.D0Efix("f", "x", bad),
                source.D0Eif0(source.D0Ebtf(True), source.D0Eint(0), bad),
                source.D0Eif0(source.D0Ebtf(False), bad, source.D0Eint(0)),
                source.D0Eop2("and", source.D0Ebtf(False), bad),
                source.D0Eop2("or", source.D0Ebtf(True), bad),
            ]
            for expression in expressions:
                with self.subTest(expression=expression):
                    with self.assertRaises(ValueError):
                        compile_expr(expression)

    def test_invalid_variable_and_binder_names(self):
        for name in ["", "1x", "x-y", "x y", "λ", None, 3]:
            expressions = [
                source.D0Evar(name), source.D0Elam(name, source.D0Eint(0)),
                source.D0Elet(name, source.D0Eint(0), source.D0Eint(1)),
                source.D0Efix(name, "x", source.D0Eint(0)),
                source.D0Efix("f", name, source.D0Eint(0)),
            ]
            for expression in expressions:
                with self.subTest(expression=expression):
                    with self.assertRaises(ValueError):
                        compile_expr(expression)

    def test_unsupported_top_level_nodes(self):
        for expression in [None, 42, True, "x", object(), Var("x"), source.D0E000()]:
            with self.subTest(expression=expression):
                with self.assertRaises(TypeError):
                    compile_expr(expression)

    def test_unsupported_source_node_inside_delayed_code(self):
        class ExtraExpression(source.D0E000):
            pass

        for expression in [
            source.D0Elam("x", ExtraExpression()),
            source.D0Eif0(source.D0Ebtf(True), source.D0Eint(1), ExtraExpression()),
        ]:
            with self.subTest(expression=expression):
                with self.assertRaises(TypeError):
                    compile_expr(expression)


if __name__ == "__main__":
    unittest.main()
