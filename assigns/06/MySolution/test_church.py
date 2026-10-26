"""
unittest tests for the eight basic builders currently in church.py

Coverage: 
ENC-01 (basic representations and closure)
ENC-02 (successor representation)
ENC-03 (projection representations)
pure target syntax

Run from assigns/06:
python3 -m unittest discover -s MySolution -p 'test_church.py' -v
"""

from __future__ import annotations

import re
import unittest

import church
from church import (
    identity,
    churchTrue,
    churchFalse,
    churchNatural,
    churchPair,
    churchFirst,
    churchSecond,
    churchSuccessor,
)
from target import Var, Lam, App, validateTarget
from scope import freeVariables
from observers import observe
from compiler import callByValueZ


def bindingShape(term, binders=()):
    """
    Describe syntax using binder distance rather than parameter spelling

    This accepts alpha-renamed encodings while distinguishing binding order
    For example, lambda a. lambda b. a differs from lambda a. lambda b. b
    A free variable remains explicitly marked so closure can be checked
    This is structural inspection only: it performs no reduction
    """
    if type(term) is Var:
        for distance, name in enumerate(reversed(binders)):
            if term.name == name:
                return ("bound", distance)
        return ("free", term.name)
    if type(term) is Lam:
        return ("lam", bindingShape(term.body, binders + (term.name,)))
    if type(term) is App:
        return (
            "app",
            bindingShape(term.function, binders),
            bindingShape(term.argument, binders),
        )
    raise TypeError(f"Unsupported target node: {type(term).__name__}")


class TestBasicChurchBuilders(unittest.TestCase):
    def assertAlphaEqual(self, actual, expected):
        """Compare the required syntax without requiring particular names"""
        self.assertEqual(bindingShape(actual), bindingShape(expected))

    def assertPureAndClosed(self, term, binders=()):
        """
        Independently inspect every node and its lexical scope.

        Do not rely solely on validateTarget: closure and identifiers must
        still be checked if that validator is not yet fully implemented.
        """
        self.assertIn(type(term), (Var, Lam, App))
        if type(term) in (Var, Lam):
            self.assertIs(type(term.name), str)
            self.assertIsNotNone(
                re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", term.name)
            )
        if type(term) is Var:
            self.assertIn(term.name, binders, f"Free variable: {term.name}")
        elif type(term) is Lam:
            self.assertPureAndClosed(term.body, binders + (term.name,))
        else:
            self.assertPureAndClosed(term.function, binders)
            self.assertPureAndClosed(term.argument, binders)

    def test_identity(self):
        self.assertAlphaEqual(identity(), Lam("value", Var("value")))

    def test_true_selects_first_parameter(self):
        expected = Lam("left", Lam("right", Var("left")))
        self.assertAlphaEqual(churchTrue(), expected)

    def test_false_selects_second_parameter(self):
        expected = Lam("left", Lam("right", Var("right")))
        self.assertAlphaEqual(churchFalse(), expected)

    def test_booleans_have_distinct_binding_shapes(self):
        self.assertNotEqual(bindingShape(churchTrue()), bindingShape(churchFalse()))

    def test_zero(self):
        # No application of the function occurs for zero.
        expected = Lam("step", Lam("base", Var("base")))
        self.assertAlphaEqual(churchNatural(0), expected)

    def test_one(self):
        expected = Lam("step", Lam("base", App(Var("step"), Var("base"))))
        self.assertAlphaEqual(churchNatural(1), expected)

    def test_three(self):
        # An explicit expected tree checks application direction and nesting.
        expected = Lam(
            "step",
            Lam(
                "base",
                App(Var("step"), App(Var("step"), App(Var("step"), Var("base")))),
            ),
        )
        self.assertAlphaEqual(churchNatural(3), expected)

    def test_numeral_spines(self):
        # Inspect literal syntax; this is not a decoder for computed numerals.
        for number in (0, 1, 2, 3, 5, 10, 25):
            with self.subTest(number=number):
                numeral = churchNatural(number)
                self.assertIs(type(numeral), Lam)
                inner = numeral.body
                self.assertIs(type(inner), Lam)
                self.assertNotEqual(numeral.name, inner.name)
                body = inner.body
                for _ in range(number):
                    self.assertIs(type(body), App)
                    self.assertEqual(body.function, Var(numeral.name))
                    body = body.argument
                self.assertEqual(body, Var(inner.name))

    def test_negative_naturals_are_rejected(self):
        for number in (-1, -5):
            with self.subTest(number=number):
                with self.assertRaises(ValueError):
                    churchNatural(number)

    def test_non_integer_naturals_are_rejected(self):
        # The builder currently uses ValueError for all invalid inputs.
        # Also accept TypeError if type/value diagnostics are split later.
        for value in (True, False, 1.0, 2.5, "3", None):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    churchNatural(value)

    def test_pair_parameter_order_and_application_order(self):
        expected = Lam(
            "left",
            Lam(
                "right",
                Lam("choose", App(App(Var("choose"), Var("left")), Var("right"))),
            ),
        )
        self.assertAlphaEqual(churchPair(), expected)

    def test_first_contains_expanded_true(self):
        # Write the expected selector independently of churchTrue().
        selector = Lam("left", Lam("right", Var("left")))
        self.assertAlphaEqual(churchFirst(), Lam("pair", App(Var("pair"), selector)))

    def test_second_contains_expanded_false(self):
        selector = Lam("left", Lam("right", Var("right")))
        self.assertAlphaEqual(churchSecond(), Lam("pair", App(Var("pair"), selector)))

    def test_successor_parameter_order_and_body(self):
        # SUCC = lambda count. lambda step. lambda base. step ((count step) base)
        expected = Lam(
            "count",
            Lam(
                "step",
                Lam(
                    "base",
                    App(Var("step"), App(App(Var("count"), Var("step")), Var("base"))),
                ),
            ),
        )
        self.assertAlphaEqual(churchSuccessor(), expected)

    def test_all_basic_combinators_are_pure_and_closed(self):
        builders = (
            identity, churchTrue, churchFalse, churchPair,
            churchFirst, churchSecond, churchSuccessor,
        )
        for builder in builders:
            with self.subTest(builder=builder.__name__):
                term = builder()
                self.assertIsNone(validateTarget(term))
                self.assertPureAndClosed(term)
        for number in (0, 1, 2, 5, 25):
            with self.subTest(builder="churchNatural", number=number):
                term = churchNatural(number)
                self.assertIsNone(validateTarget(term))
                self.assertPureAndClosed(term)


class TestChurchOperations(unittest.TestCase):
    def assertOperation(self, builder, inputs, kind, expected):
        term = builder()
        self.assertIsNone(validateTarget(term))
        self.assertEqual(freeVariables(term), set())
        for value in inputs:
            argument = (church.churchTrue() if value else church.churchFalse()) \
                if type(value) is bool else church.churchNatural(value)
            term = App(term, argument)
        result = observe(term, kind, 10000)
        self.assertEqual(result.status, 'completed', result.message)
        self.assertIs(type(result.value), type(expected))
        self.assertEqual(result.value, expected)

    def test_successor_predecessor_and_zero(self):
        for number, successor, predecessor, zero in [
            (0, 1, 0, True), (1, 2, 0, False), (4, 5, 3, False),
        ]:
            with self.subTest(number=number):
                self.assertOperation(church.churchSuccessor, [number], 'nat', successor)
                self.assertOperation(church.churchPredecessor, [number], 'nat', predecessor)
                self.assertOperation(church.churchIsZero, [number], 'bool', zero)

    def test_arithmetic_with_zero_equal_and_unequal_operands(self):
        for a, b, total, difference, product in [
            (0, 0, 0, 0, 0), (0, 3, 3, 0, 0), (3, 0, 3, 3, 0),
            (2, 2, 4, 0, 4), (2, 5, 7, 0, 10), (5, 2, 7, 3, 10),
        ]:
            with self.subTest(a=a, b=b):
                self.assertOperation(church.churchAddition, [a, b], 'nat', total)
                self.assertOperation(church.churchSubtraction, [a, b], 'nat', difference)
                self.assertOperation(church.churchMultiplication, [a, b], 'nat', product)

    def test_every_comparison_with_explicit_expected_values(self):
        builders = [church.churchLessThan, church.churchLessEqual,
                    church.churchGreaterThan, church.churchGreaterEqual,
                    church.churchEqual, church.churchNotEqual]
        for a, b, expected in [
            (0, 0, (False, True, False, True, True, False)),
            (1, 3, (True, True, False, False, False, True)),
            (3, 1, (False, False, True, True, False, True)),
            (2, 2, (False, True, False, True, True, False)),
        ]:
            for builder, answer in zip(builders, expected):
                with self.subTest(builder=builder.__name__, a=a, b=b):
                    self.assertOperation(builder, [a, b], 'bool', answer)

    def test_boolean_truth_tables(self):
        for left, right, conjunction, disjunction in [
            (False, False, False, False), (False, True, False, True),
            (True, False, False, True), (True, True, True, True),
        ]:
            with self.subTest(left=left, right=right):
                self.assertOperation(church.churchAnd, [left, right], 'bool', conjunction)
                self.assertOperation(church.churchOr, [left, right], 'bool', disjunction)
        self.assertOperation(church.churchNot, [True], 'bool', False)
        self.assertOperation(church.churchNot, [False], 'bool', True)

    def test_every_combinator_is_closed_and_pure(self):
        builders = [getattr(church, name) for name in dir(church)
                    if name.startswith('church') and name != 'churchNatural']
        for builder in builders + [church.identity, callByValueZ]:
            with self.subTest(builder=builder.__name__):
                term = builder()
                self.assertIsNone(validateTarget(term))
                self.assertEqual(freeVariables(term), set())


if __name__ == "__main__":
    unittest.main()
