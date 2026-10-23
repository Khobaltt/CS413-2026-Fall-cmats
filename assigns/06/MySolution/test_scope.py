"""
Scope and substitution: TGT-03, ACC-01; deterministic freshness policy
Requires the real visitors.py that scope.py imports. No mock replaces it

Run from assignms/06:
python3 -m unittest discover -s MySolution -p 'test_*.py' -v
"""

import unittest
from copy import deepcopy

from target import Var, Lam, App
from scope import freeVariables, allNames, substitute, FreshNames


class TestNameAnalysis(unittest.TestCase):
    def test_free_variables_and_all_names(self):
        cases = [
            (Var("x"), {"x"}, {"x"}),
            (Lam("x", Var("x")), set(), {"x"}),
            (Lam("unused", Var("y")), {"y"}, {"unused", "y"}),
            (App(Var("x"), Var("x")), {"x"}, {"x"}),
            (App(Lam("x", Var("x")), Var("x")), {"x"}, {"x"}),
            (Lam("x", App(Var("x"), Lam("y", App(Var("y"), Var("z"))))),
             {"z"}, {"x", "y", "z"}),
            (Lam("x", Lam("x", Var("x"))), set(), {"x"}),
        ]
        for term, expected_free, expected_all in cases:
            with self.subTest(term=term):
                self.assertEqual(freeVariables(term), expected_free)
                self.assertEqual(allNames(term), expected_all)

    def test_analysis_does_not_mutate_input(self):
        term = Lam("x", App(Var("x"), Var("y")))
        snapshot = deepcopy(term)
        freeVariables(term)
        allNames(term)
        self.assertEqual(term, snapshot)

    def test_unsupported_nodes(self):
        for operation in [freeVariables, allNames]:
            for term in [None, 42, Lam("x", 42), App(Var("x"), 42)]:
                with self.subTest(operation=operation.__name__, term=term):
                    with self.assertRaises(TypeError):
                        operation(term)


class TestFreshNames(unittest.TestCase):
    def test_suffix_and_reserved_names(self):
        fresh = FreshNames({"x_1", "x_3"})
        self.assertEqual([fresh.new("x") for _ in range(3)], ["x_2", "x_4", "x_5"])

    def test_always_adds_suffix(self):
        self.assertEqual(FreshNames(set()).new("x"), "x_1")

    def test_names_are_shared_across_bases(self):
        fresh = FreshNames(set())
        self.assertEqual(fresh.new("x"), "x_1")
        self.assertEqual(fresh.new("x_1"), "x_1_1")
        self.assertEqual(fresh.new("x"), "x_2")

    def test_does_not_interpret_existing_suffixes(self):
        self.assertEqual(FreshNames({"x_1_1"}).new("x_1"), "x_1_2")

    def test_fresh_instances_are_deterministic(self):
        first = FreshNames({"x_1"})
        second = FreshNames({"x_1"})
        self.assertEqual([first.new("x") for _ in range(4)],
                         [second.new("x") for _ in range(4)])


class TestSubstitute(unittest.TestCase):
    def test_variable_and_application_cases(self):
        replacement = Lam("z", Var("z"))
        self.assertEqual(substitute(Var("x"), "x", replacement), replacement)
        self.assertEqual(substitute(Var("other"), "x", replacement), Var("other"))
        self.assertEqual(substitute(App(Var("x"), Var("x")), "x", replacement),
                         App(replacement, replacement))

    def test_binder_shadows_substitution_variable(self):
        term = Lam("x", App(Var("x"), Var("y")))
        self.assertEqual(substitute(term, "x", Var("z")), term)

    def test_absent_variable_does_not_trigger_renaming(self):
        term = Lam("y", Var("z"))
        self.assertEqual(substitute(term, "x", Var("y")), term)

    def test_safe_binder_is_preserved(self):
        self.assertEqual(substitute(Lam("z", Var("x")), "x", Var("y")),
                         Lam("z", Var("y")))

    def test_capture_avoidance(self):
        result = substitute(Lam("y", Var("x")), "x", Var("y"))
        self.assertEqual(result, Lam("y_1", Var("y")))
        self.assertEqual(freeVariables(result), {"y"})

    def test_bound_occurrences_are_renamed_too(self):
        term = Lam("y", App(Var("x"), Var("y")))
        self.assertEqual(substitute(term, "x", Var("y")),
                         Lam("y_1", App(Var("y"), Var("y_1"))))

    def test_nested_shadowing_during_alpha_renaming(self):
        term = Lam("y", App(Var("x"), Lam("y", Var("y"))))
        self.assertEqual(substitute(term, "x", Var("y")),
                         Lam("y_1", App(Var("y"), Lam("y", Var("y")))))

    def test_skips_existing_bound_names(self):
        term = Lam("y", Lam("y_1", App(Var("x"), Var("y"))))
        self.assertEqual(substitute(term, "x", Var("y")),
                         Lam("y_2", Lam("y_1", App(Var("y"), Var("y_2")))))

    def test_reserves_bound_names_in_replacement(self):
        replacement = Lam("y_1", Var("y"))
        self.assertEqual(substitute(Lam("y", Var("x")), "x", replacement),
                         Lam("y_2", replacement))

    def test_shared_fresh_supply_visits_function_before_argument(self):
        term = App(Lam("y", Var("x")), Lam("y", Var("x")))
        self.assertEqual(substitute(term, "x", Var("y")),
                         App(Lam("y_1", Var("y")), Lam("y_2", Var("y"))))

    def test_closed_replacement_does_not_require_alpha_renaming(self):
        replacement = Lam("y", Var("y"))
        self.assertEqual(substitute(Lam("y", Var("x")), "x", replacement),
                         Lam("y", replacement))

    def test_inputs_are_preserved_and_calls_are_deterministic(self):
        term = Lam("y", App(Var("x"), Var("y")))
        replacement = App(Var("y"), Lam("z", Var("z")))
        term_snapshot = deepcopy(term)
        replacement_snapshot = deepcopy(replacement)
        first = substitute(term, "x", replacement)
        self.assertEqual(first, substitute(term, "x", replacement))
        self.assertEqual(term, term_snapshot)
        self.assertEqual(replacement, replacement_snapshot)

    def test_free_variable_law(self):
        replacement = App(Var("y"), Var("z"))
        cases = [
            (Var("x"), {"y", "z"}),
            (Lam("x", Var("x")), set()),
            (Lam("y", App(Var("x"), Var("w"))), {"y", "z", "w"}),
        ]
        for term, expected in cases:
            with self.subTest(term=term):
                self.assertEqual(freeVariables(substitute(term, "x", replacement)), expected)


if __name__ == "__main__":
    unittest.main()
