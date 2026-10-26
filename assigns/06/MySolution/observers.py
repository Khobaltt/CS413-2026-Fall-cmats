"""
Bounded observers: OBS-01, OBS-02, OBS-03

All computation goes through the shared evaluator
Python only inspects the final observation shapes
Execution steps are reported by the caller separately

Expected kinds: "nat", "bool", or ("pair", leftKind, rightKind)
Example nested kind: ("pair", "nat", ("pair", "bool", "nat"))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from target import Var, Lam, App, validateTarget
from evaluator import evaluate, EvaluationResult
from scope import freeVariables
from church import churchFirst, churchSecond


TargetTerm: TypeAlias = Var | Lam | App
Kind: TypeAlias = Literal["nat", "bool"] | tuple[Literal["pair"], "Kind", "Kind"]


@dataclass(frozen=True)
class ObservationResult:
    """Immutable decoding outcome; value is None unless status is completed"""

    status: Literal["completed", "exhausted", "malformed"]
    value: object
    steps: int
    message: str = ""


class MalformedObservation(ValueError):
    """The evaluated observation has an unexpected data shape"""


class ObservationExhausted(Exception):
    """Another beta-value step was needed after spending the budget"""


def runTarget(term: TargetTerm, budget: int) -> tuple[TargetTerm | None, int, bool]:
    """
    Call the shared evaluator and return (value, steps, completed)

    Invalid target syntax and open terms are malformed observation inputs
    Budget errors remain API errors
    Completion uses the evaluator's status, including when the last permitted step produces a value
    """
    if type(budget) is not int or budget < 0:
        raise ValueError("Observation budget must be a nonnegative integer")

    try:
        validateTarget(term)
    except (TypeError, ValueError) as error:
        raise MalformedObservation(str(error)) from error

    if freeVariables(term):
        raise MalformedObservation("Cannot observe an open target term")

    result = evaluate(term, budget)
    if not isinstance(result, EvaluationResult):
        raise RuntimeError("Expected a target EvaluationResult")

    completed = result.status == "completed"
    return (result.term if completed else None, result.steps, completed)


class ObservationBudget:
    """One budget shared by every evaluation in an observation call"""

    def __init__(self, limit: int):
        """Validate the total beta-value budget and start the count at zero"""
        if type(limit) is not int or limit < 0:
            raise ValueError("Observation budget must be a nonnegative integer")
        self.limit = limit
        self.steps = 0

    def evaluate(self, term: TargetTerm) -> Lam:
        """Evaluate with the remaining budget and accumulate consumed steps"""
        remaining = self.limit - self.steps
        value, used, completed = runTarget(term, remaining)
        if type(used) is not int or not 0 <= used <= remaining:
            raise RuntimeError("Evaluator returned an invalid step count")
        self.steps += used
        if not completed:
            raise ObservationExhausted("Observation step budget exhausted")
        if type(value) is not Lam:
            raise MalformedObservation("Expected a target lambda value")
        return value


def naturalStep() -> TargetTerm:
    """STEP = lam tail. lam c. lam z. c tail"""