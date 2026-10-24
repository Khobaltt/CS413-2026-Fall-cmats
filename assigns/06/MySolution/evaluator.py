"""
Shared evaluator for source and target expressions

Target evaluation:
- Weak, left-to-right call-by-value
- Lambda abstractions are values
- Count only beta-value contractions
- Do not reduce beneath lambdas
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from target import Var, Lam, App, validateTarget
from scope import freeVariables, substitute

import lambda1_vp as source


TargetTerm = Var | Lam | App


@dataclass(frozen=True)
class EvaluationResult:
    status: Literal["completed", "exhausted"]

    # Completed: resulting lambda value
    # Exhausted: expression after all permitted steps
    term: TargetTerm

    steps: int


def stepTarget(term: TargetTerm) -> TargetTerm:
    """
    Perform exactly one beta-value contraction

    Assumed: term is not already a lambda value
    """

    if type(term) is Var:
        # Raise ValueError because a free variable cannot evaluate to a lambda value
        raise ValueError(f"cannot evaluate free variable: {term.name}")

    elif type(term) is App:

        if type(term.function) is not Lam:
            # Reduce the function by one step
            # Return a new App containing the reduced function and the original argument
            return App(
                stepTarget(term.function),
                term.argument
            )

        elif type(term.argument) is not Lam:
            # Reduce the argument by one step
            # Return a new App containing the original function and the reduced argument
            return App(
                term.function,
                stepTarget(term.argument)
            )

        # Both the function and argument are lambdas
        # Perform beta-value contraction using substitute():
        #
        # (lam x. body) value -> body[x := value]
        #
        # Return the substituted body without evaluating it further
        return substitute(
            term.function.body,
            term.function.name,
            term.argument
        )

    # Raise TypeError for unsupported nodes or an attempt to step an already completed lambda
    raise TypeError(f"Unsupported target node: {type(term).__name__}")

def evaluateTarget(
    term: TargetTerm,
    budget: int,
) -> EvaluationResult:
    """
    Evaluate a valid target term under a contraction budget
    """

    # Reject budgets that are not integers or are negative
    if type(budget) is not int or budget < 0:
        raise ValueError("budget must be a nonnegative integer")

    # Apply the target structural validator
    validateTarget(term)

    # Enforce the closed-program execution policy
    if freeVariables(term):
        raise ValueError("Cannot evaluate an open target term")

    current = term
    steps = 0

    while True:

        # If current is a lambda, return a completed EvaluationResult
        # Allows a lambda to complete with budget=0 and final completed step
        if type(current) is Lam:
            return EvaluationResult("completed", current, steps)

        # Check whether the budget has been exhausted
        if steps >= budget:
            return EvaluationResult("exhausted", current, steps)

        # Perform one step using stepTarget()
        current = stepTarget(current)
        steps += 1


def evaluate(term: object, budget: int) -> EvaluationResult:
    """
    Shared evaluation entry point

    Will be extended with source cases later
    Its return annotation may also need extending for source results
    """

    if type(term) in (Var, Lam, App):
        return evaluateTarget(term, budget)

    # TODO:
    # Recognize source AST nodes and evaluate their source semantics

    raise TypeError(
        f"Unsupported expression: {type(term).__name__}"
    )