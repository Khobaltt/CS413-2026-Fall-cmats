"""
Bounded observers: OBS-01, OBS-02, OBS-03

Run from assigns/06:
python3 -m unittest discover -s MySolution -p 'test_*.py' -v
"""

import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError

from target import Var, Lam, App, validateTarget
from scope import freeVariables
from evaluator import evaluate
from church import (
    identity, churchNatural, churchTrue, churchFalse, churchPair,
    churchSuccessor, churchAddition,
)
from observers import (
    ObservationResult, ObservationBudget, ObservationExhausted,
    MalformedObservation, runTarget, alphaEquivalent, countNaturalSpine,
    naturalStep, naturalBase, trueMarker, falseMarker,
    firstProjection, secondProjection,
    observe, observeNatural, observeBoolean, observePair,
)


def makePair(left, right):
    """Construct an encoded pair expression using the real Church builder."""
    return App(App(churchPair(), left), right)


def omega():
    """A closed expression that never reaches a value under call-by-value."""
    function = Lam("x", App(Var("x"), Var("x")))
    return App(function, function)


class TestObservationResult(unittest.TestCase):
    def test_fields_and_structural_equality(self):
        result = ObservationResult("completed", (2, True), 7)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.value, (2, True))
        self.assertEqual(result.steps, 7)
        self.assertEqual(result.message, "")
        self.assertEqual(result, ObservationResult("completed", (2, True), 7))

    def test_result_is_frozen(self):
        result = ObservationResult("completed", 2, 4)
        for field, value in [("status", "malformed"), ("value", None),
                             ("steps", 0), ("message", "changed")]:
            with self.subTest(field=field):
                with self.assertRaises(FrozenInstanceError):
                    setattr(result, field, value)


class TestObservationContexts(unittest.TestCase):
    def test_contexts_are_closed_pure_target_terms(self):
        for builder in [naturalStep, naturalBase, trueMarker, falseMarker,
                        firstProjection, secondProjection]:
            with self.subTest(builder=builder.__name__):
                term = builder()
                self.assertIsNone(validateTarget(term))
                self.assertEqual(freeVariables(term), set())

    def test_boolean_markers_are_distinct(self):
        self.assertFalse(alphaEquivalent(trueMarker(), falseMarker()))

    def test_projection_contexts_select_components(self):
        pair = makePair(churchNatural(2), churchTrue())
        first = observeNatural(App(firstProjection(), pair), budget=1000)
        second = observeBoolean(App(secondProjection(), pair), budget=1000)
        self.assertEqual((first.status, first.value), ("completed", 2))
        self.assertEqual((second.status, second.value), ("completed", True))


class TestAlphaEquivalent(unittest.TestCase):
    def test_renamed_binders_and_applications(self):
        left = Lam("x", Lam("y", App(Var("x"), Var("y"))))
        right = Lam("a", Lam("b", App(Var("a"), Var("b"))))
        self.assertTrue(alphaEquivalent(left, right))
        self.assertTrue(alphaEquivalent(right, left))

    def test_shadowing_uses_nearest_binder(self):
        left = Lam("x", Lam("x", Var("x")))
        self.assertTrue(alphaEquivalent(left, Lam("a", Lam("b", Var("b")))))
        self.assertFalse(alphaEquivalent(left, Lam("a", Lam("b", Var("a")))))

    def test_free_names_must_match(self):
        self.assertTrue(alphaEquivalent(Lam("x", Var("free")),
                                        Lam("y", Var("free"))))
        self.assertFalse(alphaEquivalent(Var("x"), Var("y")))
        self.assertFalse(alphaEquivalent(Lam("x", Var("x")),
                                         Lam("y", Var("x"))))

    def test_structure_and_argument_order_matter(self):
        self.assertFalse(alphaEquivalent(Var("x"), Lam("x", Var("x"))))
        self.assertFalse(alphaEquivalent(App(Var("f"), Var("x")),
                                         App(Var("x"), Var("f"))))

    def test_comparison_does_not_evaluate(self):
        term = App(identity(), identity())
        self.assertFalse(alphaEquivalent(term, identity()))
        self.assertTrue(alphaEquivalent(omega(), omega()))

    def test_invalid_target_syntax_is_rejected(self):
        with self.assertRaises(TypeError):
            alphaEquivalent(object(), identity())


class TestNaturalSpine(unittest.TestCase):
    def test_base_accepts_renaming_and_shadowing(self):
        for term in [naturalBase(), Lam("a", Lam("b", Var("b"))),
                     Lam("x", Lam("x", Var("x")))]:
            with self.subTest(term=term):
                self.assertEqual(countNaturalSpine(term), 0)

    def test_counts_renamed_closed_nodes(self):
        tail = Lam("a", Lam("b", Var("b")))
        for expected in range(1, 5):
            tail = Lam("c", Lam("z", App(Var("c"), tail)))
            self.assertEqual(countNaturalSpine(tail), expected)

    def test_rejects_malformed_spines(self):
        cases = [
            Var("x"), identity(),
            Lam("c", Lam("z", Var("c"))),
            Lam("c", Lam("z", App(Var("z"), naturalBase()))),
            Lam("x", Lam("x", App(Var("x"), naturalBase()))),
            Lam("c", Lam("z", App(Var("c"), Lam("a", Var("c"))))),
            Lam("c", Lam("z", App(Var("c"), identity()))),
        ]
        for term in cases:
            with self.subTest(term=term):
                with self.assertRaises(MalformedObservation):
                    countNaturalSpine(term)


class TestNaturalObservation(unittest.TestCase):
    def test_zero_and_positive_numerals(self):
        for number in [0, 1, 2, 5, 10]:
            with self.subTest(number=number):
                result = observeNatural(churchNatural(number), budget=1000)
                self.assertEqual(result.status, "completed")
                self.assertEqual(result.value, number)
                self.assertIs(type(result.value), int)
                self.assertGreaterEqual(result.steps, 2)

    def test_alpha_renamed_numeral(self):
        term = Lam("step", Lam("base", App(Var("step"), Var("base"))))
        result = observeNatural(term, budget=100)
        self.assertEqual((result.status, result.value), ("completed", 1))

    def test_arithmetic_delayed_beneath_lambda(self):
        term = App(App(churchAddition(), churchNatural(2)), churchNatural(3))
        execution = evaluate(term, budget=1000)
        self.assertEqual(execution.status, "completed")
        result = observeNatural(execution.term, budget=1000)
        self.assertEqual((result.status, result.value), ("completed", 5))

    def test_execution_and_observation_counts_are_separate(self):
        term = App(churchSuccessor(), churchNatural(3))
        execution = evaluate(term, budget=1000)
        self.assertEqual(execution.status, "completed")
        executionSnapshot = deepcopy(execution)
        valueObservation = observeNatural(execution.term, budget=1000)
        fullObservation = observeNatural(term, budget=1000)
        self.assertEqual(valueObservation.value, 4)
        self.assertEqual(fullObservation.status, "completed")
        self.assertEqual(fullObservation.value, 4)
        self.assertEqual(fullObservation.steps,
                         execution.steps + valueObservation.steps)
        self.assertEqual(execution, executionSnapshot)


class TestBooleanObservation(unittest.TestCase):
    def test_true_false_and_renamed_booleans(self):
        cases = [(churchTrue(), True), (churchFalse(), False),
                 (Lam("yes", Lam("no", Var("yes"))), True),
                 (Lam("x", Lam("x", Var("x"))), False)]
        for term, expected in cases:
            with self.subTest(term=term):
                result = observeBoolean(term, budget=100)
                self.assertEqual(result.status, "completed")
                self.assertIs(result.value, expected)
                self.assertEqual(result.steps, 2)

    def test_expected_kind_disambiguates_zero_and_false(self):
        term = churchNatural(0)
        self.assertTrue(alphaEquivalent(term, churchFalse()))
        self.assertEqual(observeNatural(term, 100).value, 0)
        self.assertIs(observeBoolean(term, 100).value, False)

    def test_rejects_result_matching_neither_marker(self):
        term = Lam("t", Lam("f", Lam("a", Lam("b", Var("b")))))
        result = observeBoolean(term, budget=100)
        self.assertEqual(result.status, "malformed")
        self.assertIsNone(result.value)
        self.assertTrue(result.message)


class TestPairObservation(unittest.TestCase):
    def test_mixed_component_kinds(self):
        for left, right, leftKind, rightKind, expected in [
            (churchNatural(2), churchTrue(), "nat", "bool", (2, True)),
            (churchFalse(), churchNatural(0), "bool", "nat", (False, 0)),
        ]:
            with self.subTest(expected=expected):
                result = observePair(makePair(left, right), leftKind, rightKind, 1000)
                self.assertEqual((result.status, result.value), ("completed", expected))

    def test_nested_pair_on_right(self):
        term = makePair(churchNatural(2), makePair(churchFalse(), churchNatural(3)))
        kind = ("pair", "nat", ("pair", "bool", "nat"))
        result = observe(term, kind, budget=1000)
        self.assertEqual((result.status, result.value), ("completed", (2, (False, 3))))

    def test_nested_pair_on_left(self):
        term = makePair(makePair(churchTrue(), churchNatural(1)), churchFalse())
        result = observePair(term, ("pair", "bool", "nat"), "bool", 1000)
        self.assertEqual((result.status, result.value), ("completed", ((True, 1), False)))

    def test_nested_components_share_one_budget(self):
        # Two pair constructions cost 4 steps. Each projection costs 4.
        # Observing the three boolean leaves costs 2 steps each: 4 + 16 + 6.
        term = makePair(churchTrue(), makePair(churchFalse(), churchTrue()))
        kind = ("pair", "bool", ("pair", "bool", "bool"))
        exact = observe(term, kind, budget=26)
        self.assertEqual((exact.status, exact.value, exact.steps),
                         ("completed", (True, (False, True)), 26))
        short = observe(term, kind, budget=25)
        self.assertEqual((short.status, short.value, short.steps),
                         ("exhausted", None, 25))

    def test_malformed_second_component_returns_no_partial_answer(self):
        bad = Lam("t", Lam("f", Lam("a", Lam("b", Var("b")))))
        result = observePair(makePair(churchTrue(), bad), "bool", "bool", 1000)
        self.assertEqual(result.status, "malformed")
        self.assertIsNone(result.value)
        self.assertGreater(result.steps, 0)

    def test_pair_construction_evaluates_both_components(self):
        term = makePair(churchNatural(1), omega())
        result = observePair(term, "nat", "nat", 20)
        self.assertEqual((result.status, result.value, result.steps),
                         ("exhausted", None, 20))


class TestObservationBudgets(unittest.TestCase):
    def test_zero_budget_can_evaluate_a_lambda(self):
        value, steps, completed = runTarget(identity(), budget=0)
        self.assertEqual(value, identity())
        self.assertEqual(steps, 0)
        self.assertTrue(completed)

    def test_zero_budget_cannot_apply_observation_context(self):
        for term, kind in [(churchNatural(0), "nat"), (churchTrue(), "bool")]:
            with self.subTest(kind=kind):
                result = observe(term, kind, budget=0)
                self.assertEqual((result.status, result.value, result.steps),
                                 ("exhausted", None, 0))

    def test_completion_on_last_permitted_step(self):
        for term, kind, expected in [(churchNatural(0), "nat", 0),
                                     (churchTrue(), "bool", True)]:
            with self.subTest(kind=kind):
                result = observe(term, kind, budget=2)
                self.assertEqual((result.status, result.value, result.steps),
                                 ("completed", expected, 2))
                short = observe(term, kind, budget=1)
                self.assertEqual((short.status, short.value, short.steps),
                                 ("exhausted", None, 1))

    def test_budget_state_accumulates_across_calls(self):
        state = ObservationBudget(2)
        term = App(identity(), identity())
        self.assertEqual(state.evaluate(term), identity())
        self.assertEqual(state.steps, 1)
        self.assertEqual(state.evaluate(term), identity())
        self.assertEqual(state.steps, 2)
        self.assertEqual(state.evaluate(identity()), identity())
        with self.assertRaises(ObservationExhausted):
            state.evaluate(term)
        self.assertEqual(state.steps, 2)

    def test_divergence_exhausts_instead_of_becoming_malformed(self):
        result = observeNatural(omega(), budget=25)
        self.assertEqual((result.status, result.value, result.steps),
                         ("exhausted", None, 25))
        self.assertTrue(result.message)

    def test_divergence_hidden_in_numeral_body_is_bounded(self):
        term = Lam("f", Lam("x", omega()))
        result = observeNatural(term, budget=25)
        self.assertEqual((result.status, result.value, result.steps),
                         ("exhausted", None, 25))

    def test_invalid_budgets_raise_value_error(self):
        for budget in [-1, True, False, 1.5, "10", None]:
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    observeNatural(churchNatural(0), budget)
                with self.assertRaises(ValueError):
                    ObservationBudget(budget)
                with self.assertRaises(ValueError):
                    runTarget(identity(), budget)


class TestObservationValidation(unittest.TestCase):
    def test_invalid_kinds_raise_value_error(self):
        for kind in ["int", None, (), ("pair", "nat"),
                     ("pair", "nat", "bool", "nat"),
                     ["pair", "nat", "bool"],
                     ("pair", "nat", ("pair", "bool", "invalid"))]:
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    observe(churchNatural(0), kind, budget=100)

    def test_invalid_syntax_and_open_terms_are_malformed(self):
        for term in [None, 42, object(), Var("free"),
                     Lam("x", Var("free")), Lam("bad-name", Var("bad-name")),
                     Lam("x", 42), App(identity(), Var("free"))]:
            with self.subTest(term=term):
                result = observeNatural(term, budget=100)
                self.assertEqual((result.status, result.value, result.steps),
                                 ("malformed", None, 0))
                self.assertTrue(result.message)

    def test_closed_lambda_with_bad_natural_shape_is_malformed(self):
        term = Lam("f", Lam("x", identity()))
        result = observeNatural(term, budget=100)
        self.assertEqual(result.status, "malformed")
        self.assertIsNone(result.value)
        self.assertEqual(result.steps, 2)

    def test_repeated_observation_is_deterministic_and_immutable(self):
        term = makePair(App(churchSuccessor(), churchNatural(2)), churchFalse())
        snapshot = deepcopy(term)
        first = observePair(term, "nat", "bool", budget=1000)
        second = observePair(term, "nat", "bool", budget=1000)
        self.assertEqual(first.status, "completed")
        self.assertEqual(first.value, (3, False))
        self.assertEqual(first, second)
        self.assertEqual(term, snapshot)


if __name__ == "__main__":
    unittest.main()
