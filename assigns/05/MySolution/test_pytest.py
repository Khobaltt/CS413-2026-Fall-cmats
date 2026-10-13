# independent pytest test functions, using plain assert
from contextlib import ExitStack
from copy import deepcopy
from unittest.mock import patch
import pytest
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


# every parameter set becomes a separate pytest test; only example data is shared
# check exact pretty-printing output
@pytest.mark.parametrize("label,expression,expected", PRETTY_CASES)
def test_pretty(label, expression, expected):
    # exact equality checks spacing, spelling, and nesting for every constructor
    assert d0exp_pretty(expression) == expected


# check substitution, freshness, and scope-aware renaming
@pytest.mark.parametrize("label,expression,target,replacement,expected", SUBSTITUTION_CASES)
def test_substitution(label, expression, target, replacement, expected):
    # fixed strings check structure as well as capture avoidance
    assert d0exp_pretty(d0exp_substitute(expression, target, replacement)) == expected


# check unchanged inputs and repeatable results
@pytest.mark.parametrize("label,expression,target,replacement,expected", SUBSTITUTION_CASES)
def test_preservation_and_determinism(label, expression, target, replacement, expected):
    # snapshot the input trees, then check that repeated calls agree exactly
    before_e, before_r = deepcopy(expression), deepcopy(replacement)
    d0exp_pretty(expression)
    d0exp_pretty(replacement)
    first = d0exp_substitute(expression, target, replacement)
    second = d0exp_substitute(expression, target, replacement)
    assert expression == before_e
    assert replacement == before_r
    assert first == second
    assert d0exp_pretty(second) == expected


# check explicit free-variable sets using scope rules
@pytest.mark.parametrize("expression,target,replacement,expected", FV_CASES)
def test_explicit_free_variables(expression, target, replacement, expected):
    # check explicit free-name sets, then independently check the required equation
    result = d0exp_substitute(expression, target, replacement)
    original = d0exp_fvset(expression)
    formula = ((original - {target}) | d0exp_fvset(replacement)
               if target in original else original)
    assert d0exp_fvset(result) == expected
    assert d0exp_fvset(result) == formula


# check the free-variable property and absent targets
@pytest.mark.parametrize("label,expression,target,replacement,expected", SUBSTITUTION_CASES)
def test_property_for_all_examples(label, expression, target, replacement, expected):
    # An absent target must preserve free names and exact AST structure.
    result = d0exp_substitute(expression, target, replacement)
    original = d0exp_fvset(expression)
    formula = ((original - {target}) | d0exp_fvset(replacement)
               if target in original else original)
    assert d0exp_fvset(result) == formula
    if target not in original:
        assert result == expression


# check inserting the replacement without traversing it
def test_insert_once():
    # identity verifies that substitution does not recurse into the replacement
    replacement = SUBSTITUTION_CASES[4][3]
    assert d0exp_substitute(D0Evar("x"), "x", replacement) is replacement


# check that printing and substitution must not evaluate
def test_no_evaluation():
    # instrument every evaluator method; syntax visitors must never call them
    with ExitStack() as stack:
        for name in D0ExpVisitor.__abstractmethods__:
            stack.enter_context(patch.object(EvaluateVisitor, name,
                                             side_effect=AssertionError("evaluated")))
        for _, expression, expected in PRETTY_CASES:
            assert d0exp_pretty(expression) == expected
        for _, expression, target, replacement, expected in SUBSTITUTION_CASES:
            assert d0exp_pretty(d0exp_substitute(expression, target, replacement)) == expected


# check that operations use the supplied accept/visitor interface
def test_direct_dispatch():
    # confirm both operations are actual visitors for the supplied AST interface
    expression = D0Evar("x")
    assert expression.accept(PrettyPrintVisitor()) == "x"
    reserved = expression.accept(AllNamesVisitor()) | {"y"}
    visitor = SubstitutionVisitor("x", D0Evar("y"), FreshNames(reserved))
    assert expression.accept(visitor) == D0Evar("y")
