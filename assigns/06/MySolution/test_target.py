"""
Target syntax and printing: TGT-01, TGT-02, ACC-13

Run from assigns/06:
python3 -m unittest discover -s MySolution -p 'test_*.py' -v
"""

import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError

from target import Var, Lam, App, pretty, validateTarget


class TestTargetNodes(unittest.TestCase):
    def test_fields_and_structural_equality(self):
        term = App(Lam("x", Var("x")), Var("y"))
        self.assertEqual(term.function.name, "x")
        self.assertEqual(term.function.body, Var("x"))
        self.assertEqual(term.argument, Var("y"))
        self.assertEqual(term, App(Lam("x", Var("x")), Var("y")))
        self.assertNotEqual(Var("x"), Var("y"))

    def test_nodes_are_frozen(self):
        for node, field, value in [
            (Var("x"), "name", "y"),
            (Lam("x", Var("x")), "name", "y"),
            (Lam("x", Var("x")), "body", Var("y")),
            (App(Var("f"), Var("x")), "function", Var("g")),
            (App(Var("f"), Var("x")), "argument", Var("y")),
        ]:
            with self.subTest(node=node, field=field):
                with self.assertRaises(FrozenInstanceError):
                    setattr(node, field, value)


class TestPretty(unittest.TestCase):
    def test_exact_notation(self):
        cases = [
            (Var("x"), "x"),
            (Lam("x", Var("x")), "(lam x. x)"),
            (App(Var("f"), Var("x")), "(f x)"),
            (App(Lam("x", Var("x")), Var("y")), "((lam x. x) y)"),
            (Lam("x", Lam("y", App(Var("x"), Var("y")))), "(lam x. (lam y. (x y)))"),
            (App(App(Var("f"), Var("x")), Var("y")), "((f x) y)"),
            (App(Var("f"), App(Var("x"), Var("y"))), "(f (x y))"),
        ]
        for term, expected in cases:
            with self.subTest(term=term):
                self.assertEqual(pretty(term), expected)

    def test_printing_does_not_evaluate_or_mutate(self):
        term = App(Lam("x", Var("x")), Var("y"))
        snapshot = deepcopy(term)
        self.assertEqual(pretty(term), "((lam x. x) y)")
        self.assertEqual(term, snapshot)

    def test_unsupported_node(self):
        with self.assertRaises(TypeError):
            pretty(object())


class TestValidateTarget(unittest.TestCase):
    def test_valid_identifiers_and_open_terms(self):
        for name in ["x", "PLUS", "s", "z", "t", "f", "_", "_fresh0", "x_12", "Ab9"]:
            with self.subTest(name=name):
                self.assertIsNone(validateTarget(Var(name)))
                self.assertIsNone(validateTarget(Lam(name, Var("free"))))
        self.assertIsNone(validateTarget(App(Lam("x", Var("x")), Var("y"))))

    def test_nonstring_names(self):
        for name in [None, 3, True, ["x"]]:
            for term in [Var(name), Lam(name, Var("x"))]:
                with self.subTest(term=term):
                    with self.assertRaises(ValueError):
                        validateTarget(term)

    def test_identifier_policy(self):
        # Section 3.1: [A-Za-z_][A-Za-z0-9_]*.
        for name in ["", "1x", "x-y", "x y", "x.y", "x\n", "é", "λ"]:
            for term in [Var(name), Lam(name, Var("x"))]:
                with self.subTest(term=term):
                    with self.assertRaises(ValueError):
                        validateTarget(term)

    def test_rejects_unsupported_nodes_recursively(self):
        for term in [42, True, None, "x", object(),
                     Lam("x", 42), App(42, Var("x")), App(Var("f"), 42)]:
            with self.subTest(term=term):
                with self.assertRaises(TypeError):
                    validateTarget(term)

    def test_rejects_subclasses_as_additional_node_forms(self):
        class ExtraVar(Var):
            pass

        with self.assertRaises(TypeError):
            validateTarget(ExtraVar("x"))


if __name__ == "__main__":
    unittest.main()
