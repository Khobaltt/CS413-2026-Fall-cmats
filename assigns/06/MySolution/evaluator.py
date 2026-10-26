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

def lookupSource(
    environment: source.ENV000,
    name: str,
) -> source.D0V000:
    """Return the value from the nearest matching binding"""

    current = environment

    while isinstance(current, source.ENVcns):
        if current.arg1 == name:
            return current.arg2

        current = current.arg3

    raise ValueError(f"Unbound source variable: {name}")

class SourceEvaluator(source.D0ExpVisitor[source.D0V000]):
    """Evaluate source expressions using lexical environments"""

    def __init__(
        self,
        environment: source.ENV000 | None = None,
    ) -> None:
        if environment is None:
            environment = source.ENVnil()

        self.environment = environment

    def visit_int(self, expression):
        # Source integers represent natural numbers
        if type(expression.arg1) is not int or expression.arg1 < 0:
            raise ValueError(f"Unsupported natural literal: {expression.arg1!r}")

        return source.D0Vint(expression.arg1)

    def visit_btf(self, expression):
        if type(expression.arg1) is not bool:
            raise ValueError(f"Invalid boolean literal: {expression.arg1!r}")

        return source.D0Vbtf(expression.arg1)

    def visit_var(self, expression):
        return lookupSource(self.environment, expression.arg1)

    def visit_lam(self, expression):
        # Capture the defining environment
        # Do not evaluate the function body yet
        return source.D0Vlam(self.environment, expression)

    def visit_fix(self, expression):
        # Store the recursive function and its defining environment
        # Its body runs only when the function is applied
        return source.D0Vfix(self.environment, expression)

    def visit_app(self, expression):
        # Evaluate function first, then argument
        function = expression.arg1.accept(self)
        argument = expression.arg2.accept(self)

        if isinstance(function, source.D0Vlam):
            definition = function.arg2

            # Extend the function's defining environment
            environment = source.ENVcns(
                definition.arg1,
                argument,
                function.arg1,
            )

            return definition.arg2.accept(
                SourceEvaluator(environment)
            )

        if isinstance(function, source.D0Vfix):
            definition = function.arg2

            # Bind the recursive function name first
            environment = source.ENVcns(
                definition.arg1,
                function,
                function.arg1,
            )

            # Bind the parameter second so it shadows the function name when both names are identical
            environment = source.ENVcns(
                definition.arg2,
                argument,
                environment,
            )

            return definition.arg3.accept(
                SourceEvaluator(environment)
            )

        raise TypeError("Source application requires a function")

    def visit_let(self, expression):
        # Evaluate the initializer in the original environment
        value = expression.arg2.accept(self)

        # The new binding is available only inside the body
        environment = source.ENVcns(
            expression.arg1,
            value,
            self.environment,
        )

        return expression.arg3.accept(
            SourceEvaluator(environment)
        )

    def visit_if0(self, expression):
        condition = expression.arg1.accept(self)

        if not isinstance(condition, source.D0Vbtf):
            raise TypeError("Conditional requires a boolean")

        # Evaluate only the selected branch
        if condition.arg1:
            return expression.arg2.accept(self)

        return expression.arg3.accept(self)

    def visit_pair(self, expression):
        # Both components must evaluate, in this order
        first = expression.arg1.accept(self)
        second = expression.arg2.accept(self)

        return source.D0Vpair(first, second)

    def visit_pfst(self, expression):
        pair = expression.arg1.accept(self)

        if not isinstance(pair, source.D0Vpair):
            raise TypeError("First projection requires a pair")

        return pair.arg1

    def visit_psnd(self, expression):
        pair = expression.arg1.accept(self)

        if not isinstance(pair, source.D0Vpair):
            raise TypeError("Second projection requires a pair")

        return pair.arg2

    def visit_op1(self, expression):
        if expression.name != "not":
            raise ValueError(f"Unsupported unary operator: {expression.name!r}")

        value = expression.arg1.accept(self)

        if not isinstance(value, source.D0Vbtf):
            raise TypeError("'not' requires a boolean")

        return source.D0Vbtf(not value.arg1)

    def visit_op2(self, expression):
        operator = expression.name

        supported = {
            "+", "-", "*",
            "<", "<=", ">", ">=", "==", "!=",
            "and", "or",
        }

        if operator not in supported:
            raise ValueError(f"Unsupported binary operator: {operator!r}")

        left = expression.arg1.accept(self)

        if operator in ("and", "or"):
            if not isinstance(left, source.D0Vbtf):
                raise TypeError(f"{operator!r} requires boolean operands")

            # Short-circuit before evaluating the right operand
            if operator == "and" and not left.arg1:
                return source.D0Vbtf(False)

            if operator == "or" and left.arg1:
                return source.D0Vbtf(True)

            right = expression.arg2.accept(self)

            if not isinstance(right, source.D0Vbtf):
                raise TypeError(f"{operator!r} requires boolean operands")

            # In the remaining cases, the answer is the right value
            return right

        # Arithmetic and comparisons evaluate both operands
        right = expression.arg2.accept(self)

        if (
            not isinstance(left, source.D0Vint)
            or not isinstance(right, source.D0Vint)
        ):
            raise TypeError(f"{operator!r} requires natural-number operands")

        a = left.arg1
        b = right.arg1

        match operator:
            case "+":
                return source.D0Vint(a + b)
            case "-":
                return source.D0Vint(max(a - b, 0))
            case "*":
                return source.D0Vint(a * b)
            case "<":
                return source.D0Vbtf(a < b)
            case "<=":
                return source.D0Vbtf(a <= b)
            case ">":
                return source.D0Vbtf(a > b)
            case ">=":
                return source.D0Vbtf(a >= b)
            case "==":
                return source.D0Vbtf(a == b)
            case "!=":
                return source.D0Vbtf(a != b)

        raise ValueError(f"Unsupported operator: {operator!r}")

def evaluate(
    term: object, 
    budget: int | None = None,
) -> EvaluationResult | source.D0V000:
    """
    Shared evaluation entry point

    Source expressions return source-language values
    Target terms require a budget and return an EvaluationResult
    """

    # Recognize target nodes
    if type(term) in (Var, Lam, App):
        if budget is None:
            raise ValueError("Target evaluation requires a budget")
        return evaluateTarget(term, budget)

    # Recognize source AST nodes and evaluate their source semantics
    if isinstance(term, source.D0E000):
        return term.accept(SourceEvaluator())

    raise TypeError(
        f"Unsupported expression: {type(term).__name__}"
    )