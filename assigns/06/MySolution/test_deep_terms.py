"""
Regression tests for explicit-stack traversal and large numeral observation.

Run from assigns/06:
python3 -m unittest discover -s MySolution -p 'test_*.py' -v

Do not use recursive dataclass equality, repr, or deepcopy for deep test trees.
Use binding-aware iterative comparison and direct field inspection instead.
"""

import unittest

import lambda1_vp as source
from church import churchNatural, identity
from compiler import compile_expr
from evaluator import evaluate, stepTarget
from observers import (alphaEquivalent, countNaturalSpine, naturalBase,
                       MalformedObservation, observeNatural)
from scope import freeVariables, allNames, substitute, _renameBound
from target import Var, Lam, App, pretty, validateTarget


def wrapLambdas(term, name, depth):
    for _ in range(depth):
        term = Lam(name, term)
    return term


class TestDeepTargetOperations(unittest.TestCase):
    depth = 1500

    def test_large_literal_compiles_and_prints_exactly(self):
        term = compile_expr(source.D0Eint(self.depth))
        expected = '(lam f. (lam x. ' + '(f ' * self.depth + 'x' + ')' * self.depth + '))'
        self.assertEqual(pretty(term), expected)
        self.assertIsNone(validateTarget(term))
        result = evaluate(term, 0)
        self.assertEqual((result.status, result.steps), ('completed', 0))
        self.assertIs(result.term, term)

    def test_deep_invalid_tail_is_rejected(self):
        for tail, error in [(42, TypeError), (Var('bad-name'), ValueError)]:
            with self.subTest(error=error):
                with self.assertRaises(error):
                    validateTarget(wrapLambdas(tail, 'x', self.depth))

    def test_identifier_error_contains_actual_value(self):
        with self.assertRaisesRegex(ValueError, 'Expected a string, got 42'):
            validateTarget(Var(42))

    def test_deep_free_variables_restore_scope_between_siblings(self):
        term = App(wrapLambdas(App(Var('x'), Var('free')), 'x', self.depth), Var('x'))
        self.assertEqual(freeVariables(term), {'free', 'x'})
        self.assertEqual(allNames(term), {'free', 'x'})

    def test_all_names_retains_unused_deep_binders(self):
        term = Var('free')
        names = {f'binder_{index}' for index in range(self.depth)}
        for name in sorted(names):
            term = Lam(name, term)
        self.assertEqual(allNames(term), names | {'free'})
        self.assertEqual(freeVariables(term), {'free'})

    def test_deep_renaming_preserves_nested_shadowing(self):
        shadow = Lam('old', Var('old'))
        body = wrapLambdas(App(Var('old'), shadow), 'padding', self.depth)
        result = _renameBound(body, 'old', 'fresh')
        for _ in range(self.depth):
            self.assertEqual(result.name, 'padding')
            result = result.body
        self.assertEqual(result.function.name, 'fresh')
        self.assertIs(result.argument, shadow)
        self.assertEqual(freeVariables(body), {'old'})

    def test_substitution_beneath_deep_binders_preserves_inputs(self):
        term = wrapLambdas(Var('target'), 'padding', self.depth)
        replacement = Lam('value', Var('value'))
        result = substitute(term, 'target', replacement)
        for _ in range(self.depth):
            self.assertEqual(result.name, 'padding')
            result = result.body
        self.assertIs(result, replacement)
        self.assertEqual(freeVariables(term), {'target'})

    def test_capture_avoidance_with_deep_replacement(self):
        replacement = wrapLambdas(Var('y'), 'padding', self.depth)
        term = Lam('y', App(Var('target'), Var('y')))
        result = substitute(term, 'target', replacement)
        self.assertEqual(result.name, 'y_1')
        self.assertIs(result.body.function, replacement)
        self.assertEqual(result.body.argument.name, 'y_1')
        self.assertEqual(freeVariables(result), {'y'})
        self.assertEqual(term.name, 'y')

    def test_one_step_through_deep_function_and_argument_contexts(self):
        value = identity()
        term = App(value, value)
        for _ in range(self.depth):
            term = App(term, value)
        result = evaluate(term, 1)
        self.assertEqual((result.status, result.steps), ('exhausted', 1))
        current = result.term
        applications = 0
        while type(current) is App:
            self.assertIs(current.argument, value)
            current = current.function
            applications += 1
        self.assertEqual(applications, self.depth)
        self.assertIs(current, value)

        term = App(value, value)
        for _ in range(self.depth):
            term = App(value, term)
        current = stepTarget(term)
        applications = 0
        while type(current) is App:
            self.assertIs(current.function, value)
            current = current.argument
            applications += 1
        self.assertEqual(applications, self.depth)
        self.assertIs(current, value)

    def test_deep_alpha_equivalence_and_shadowing(self):
        left = wrapLambdas(Var('x'), 'x', self.depth)
        right = wrapLambdas(Var('renamed'), 'renamed', self.depth)
        self.assertTrue(alphaEquivalent(left, right))
        self.assertFalse(alphaEquivalent(left, wrapLambdas(Var('free'), 'renamed', self.depth)))
        # After comparing one sibling, binder state must be restored.
        self.assertFalse(alphaEquivalent(App(left, Var('x')), App(right, Var('renamed'))))
        self.assertTrue(alphaEquivalent(App(left, Var('free')), App(right, Var('free'))))

    def test_deep_natural_spine_and_malformed_tail(self):
        spine = naturalBase()
        for _ in range(self.depth):
            spine = Lam('selector', Lam('base', App(Var('selector'), spine)))
        self.assertEqual(countNaturalSpine(spine), self.depth)
        bad = wrapLambdas(Var('free'), 'x', self.depth)
        with self.assertRaises(MalformedObservation):
            countNaturalSpine(bad)

    def test_previously_crashing_numerals_and_exact_observation_budget(self):
        for number in (350, 1000):
            with self.subTest(number=number):
                term = compile_expr(source.D0Eint(number))
                snapshot = pretty(term)
                result = observeNatural(term, number + 2)
                self.assertEqual((result.status, result.value, result.steps),
                                 ('completed', number, number + 2))
                short = observeNatural(term, number + 1)
                self.assertEqual((short.status, short.value, short.steps),
                                 ('exhausted', None, number + 1))
                self.assertEqual(pretty(term), snapshot)


if __name__ == '__main__':
    unittest.main()
