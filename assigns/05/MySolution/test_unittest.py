# standard-library tests, using TestCase methods
import unittest
from contextlib import ExitStack
from copy import deepcopy
from unittest.mock import patch
from lambda1_vp import (
    D0Evar, 
    D0ExpVisitor, 
    EvaluateVisitor, 
    d0exp_fvset
)
from MySolution.examples import (
    PRETTY_CASES, 
    SUBSTITUTION_CASES, 
    FV_CASES
)
from MySolution.visitors import (
    PrettyPrintVisitor, 
    SubstitutionVisitor, 
    FreshNames, 
    AllNamesVisitor,
    d0exp_pretty, 
    d0exp_substitute
)

# named subtests report the specific example if an assertion fails
class VisitorTests(unittest.TestCase):

    # check exact pretty-printing output
    def test_pretty_examples(self):
        # exact strings check every character, not just similar-looking output
        for label, expression, expected in PRETTY_CASES:
            with self.subTest(label=label):
                self.assertEqual(d0exp_pretty(expression), expected)

    # check substitution, freshness, and scope-aware renaming
    def test_substitution_examples(self):
        # fixed expected syntax detects capture, shadowing, and fresh-name mistakes
        for label, expression, target, replacement, expected in SUBSTITUTION_CASES:
            with self.subTest(label=label):
                result = d0exp_substitute(expression, target, replacement)
                self.assertEqual(d0exp_pretty(result), expected)

    # check unchanged inputs and repeatable results
    def test_preservation_and_determinism(self):
        # whole-tree snapshots detect any changes to either input, including binders
        for label, expression, target, replacement, expected in SUBSTITUTION_CASES:
            with self.subTest(label=label):
                before_e, before_r = deepcopy(expression), deepcopy(replacement)
                d0exp_pretty(expression)
                d0exp_pretty(replacement)
                first = d0exp_substitute(expression, target, replacement)
                second = d0exp_substitute(expression, target, replacement)
                self.assertEqual(expression, before_e)
                self.assertEqual(replacement, before_r)
                self.assertEqual(first, second)
                self.assertEqual(d0exp_pretty(second), expected)

    # check explicit free-variable sets using scope rules
    def test_explicit_free_variables(self):
        # check independently written free-name sets as well as the formula
        for expression, target, replacement, expected in FV_CASES:
            with self.subTest(expression=expression):
                actual = d0exp_fvset(d0exp_substitute(expression, target, replacement))
                original = d0exp_fvset(expression)
                formula = ((original - {target}) | d0exp_fvset(replacement)
                           if target in original else original)
                self.assertEqual(actual, expected)
                self.assertEqual(actual, formula)

    # check the free-variable property and absent targets
    def test_property_for_all_examples(self):
        # with no free target, structural equality is stronger than alpha-equivalence
        for label, expression, target, replacement, _ in SUBSTITUTION_CASES:
            with self.subTest(label=label):
                result = d0exp_substitute(expression, target, replacement)
                original = d0exp_fvset(expression)
                expected = ((original - {target}) | d0exp_fvset(replacement)
                            if target in original else original)
                self.assertEqual(d0exp_fvset(result), expected)
                if target not in original:
                    self.assertEqual(result, expression)

    # check inserting the replacement without traversing it
    def test_replacement_inserted_once(self):
        # identity proves that a replacement containing x is inserted as-is
        replacement = SUBSTITUTION_CASES[4][3]
        self.assertIs(d0exp_substitute(D0Evar("x"), "x", replacement), replacement)

    # check that printing and substitution must not evaluate
    def test_no_evaluation(self):
        # fail immediately if any supplied evaluator method is accidentally called
        with ExitStack() as stack:
            for name in D0ExpVisitor.__abstractmethods__:
                stack.enter_context(patch.object(EvaluateVisitor, name,
                                                 side_effect=AssertionError("evaluated")))
            for _, expression, expected in PRETTY_CASES:
                self.assertEqual(d0exp_pretty(expression), expected)
            for _, expression, target, replacement, expected in SUBSTITUTION_CASES:
                self.assertEqual(d0exp_pretty(d0exp_substitute(expression, target, replacement)), expected)

    # check that operations use the supplied accept/visitor interface
    def test_direct_dispatch(self):
        # both visitor result types must be obtained through the existing accept method
        expression = D0Evar("x")
        self.assertEqual(expression.accept(PrettyPrintVisitor()), "x")
        reserved = expression.accept(AllNamesVisitor()) | {"y"}
        visitor = SubstitutionVisitor("x", D0Evar("y"), FreshNames(reserved))
        self.assertEqual(expression.accept(visitor), D0Evar("y"))