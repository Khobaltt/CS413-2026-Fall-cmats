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

    return Lam('tail', Lam('c', Lam('z', App(Var('c'), Var('tail')))))


def naturalBase() -> TargetTerm:
    """BASE = lam c. lam z. z"""

    return Lam('c', Lam('z', Var('z')))


def trueMarker() -> TargetTerm:
    """A closed marker with one binder."""

    return Lam('marker', Var('marker'))


def falseMarker() -> TargetTerm:
    """A distinct closed marker; neither marker is a runtime primitive."""

    return Lam('marker', Lam('inner', Var('marker')))


def firstProjection() -> TargetTerm:
    # Return the expanded selector rather than a free FIRST abbreviation
    return churchFirst()


def secondProjection() -> TargetTerm:
    # Return the expanded selector rather than a free SECOND abbreviation
    return churchSecond()


def alphaEquivalent(left: TargetTerm, right: TargetTerm) -> bool:
    """Compare binding structure iteratively without reducing either term."""

    validateTarget(left)
    validateTarget(right)
    # Map each active name to a stack of binder depths
    # Separate stacks distinguish shadowing from coincident free names
    leftBound = {}
    rightBound = {}
    # Visit corresponding nodes together, leaving each binder after its body
    pending = [('visit', left, right, 0)]

    while pending:

        action, first, second, depth = pending.pop()

        if action == 'leave':
            # Restore the bindings that were active before these lambdas
            leftBound[first].pop()
            rightBound[second].pop()

            if not leftBound[first]:
                del leftBound[first]

            if not rightBound[second]:
                del rightBound[second]
            continue
        # Alpha-renaming changes binder names, but cannot change node structure
        if type(first) is not type(second):
            return False

        if type(first) is Var:
            # The most recent depth identifies the nearest binder for each occurrence
            firstBinding = leftBound.get(first.name)
            secondBinding = rightBound.get(second.name)

            if firstBinding is None or secondBinding is None:
                # A free occurrence cannot correspond to a bound occurrence
                if firstBinding is not None or secondBinding is not None:
                    return False
                # Free names must match literally; only bound names may be renamed
                if first.name != second.name:
                    return False
            # Bound occurrences must refer to corresponding enclosing lambdas
            elif firstBinding[-1] != secondBinding[-1]:
                return False

        elif type(first) is Lam:
            # Associate both binders with the same depth before visiting their bodies
            leftBound.setdefault(first.name, []).append(depth)
            rightBound.setdefault(second.name, []).append(depth)
            pending.append(('leave', first.name, second.name, depth))
            pending.append(('visit', first.body, second.body, depth + 1))

        else:
            # Compare function before argument, restoring binder scope between siblings
            pending.append(('visit', first.argument, second.argument, depth))
            pending.append(('visit', first.function, second.function, depth))
    return True


def countNaturalSpine(term: TargetTerm) -> int:
    """Inspect STEP/BASE shapes in one pass without evaluating their bodies.

    Each node must select its own first binder; BASE must select its own
    second binder. Parsing the entire tail this way also establishes closure,
    without repeatedly traversing all remaining nodes at every spine position.
    """

    try:
        validateTarget(term)

    except (TypeError, ValueError) as error:
        raise MalformedObservation(str(error)) from error
    # Each accepted STEP node adds one; BASE marks the end of the spine
    count = 0
    current = term

    while True:

        # Every spine node has exactly two enclosing lambda binders
        if type(current) is not Lam or type(current.body) is not Lam:
            raise MalformedObservation('Expected a STEP/BASE spine node')
        body = current.body.body
        # BASE selects the second binder, including when the binder names coincide
        if type(body) is Var and body.name == current.body.name:
            return count
        # Equal binder names make this occurrence refer to the inner binder.
        if (current.name == current.body.name or type(body) is not App
                or type(body.function) is not Var
                or body.function.name != current.name):
            raise MalformedObservation('Invalid natural spine selector')
        # STEP passes its tail to the first binder; inspect that tail next
        # This counts the final data shape without reducing lambda bodies in Python
        current = body.argument
        count += 1


def validateKind(kind: object) -> None:
    """Check natural, boolean, and recursively nested pair kinds"""

    # Scalar kinds specify how to interpret an otherwise untyped Church value
    if type(kind) is str and kind in ('nat', 'bool'):
        return
    # A pair kind carries a separate expected kind for each component
    if type(kind) is tuple and len(kind) == 3 and kind[0] == 'pair':
        validateKind(kind[1])
        validateKind(kind[2])
        return
    raise ValueError(f'Unsupported observation kind: {kind!r}')


def observeValue(term: TargetTerm, kind: Kind, state: ObservationBudget):
    """Perform all encoded work through one bounded evaluator state."""

    if kind == 'nat':
        # Evaluate term STEP BASE through the shared evaluator before inspecting its spine
        spine = state.evaluate(App(App(term, naturalStep()), naturalBase()))
        return countNaturalSpine(spine)

    if kind == 'bool':
        # Let the encoded boolean choose between distinct closed lambda markers
        marker = state.evaluate(App(App(term, trueMarker()), falseMarker()))

        if alphaEquivalent(marker, trueMarker()):
            return True

        if alphaEquivalent(marker, falseMarker()):
            return False
        raise MalformedObservation('Boolean selected neither marker')

    # Evaluate the pair before projecting; all projections and components share state
    pair = state.evaluate(term)
    # Project and observe the left component before moving to the right component
    left = state.evaluate(App(firstProjection(), pair))
    leftValue = observeValue(left, kind[1], state)
    right = state.evaluate(App(secondProjection(), pair))
    rightValue = observeValue(right, kind[2], state)
    return (leftValue, rightValue)


def observe(term: TargetTerm, kind: Kind, budget: int) -> ObservationResult:
    """Decode under one observation budget, separate from program execution.

    Invalid budgets/kinds are API errors. Invalid target syntax, open terms,
    and unrecognized final shapes produce a malformed outcome. Exhaustion
    produces no partial decoded value. This is not a type checker for every
    possible untyped Church term.
    """

    # Invalid kinds and budgets remain API errors instead of malformed data outcomes
    validateKind(kind)
    state = ObservationBudget(budget)
    try:
        # Validate even when the budget is zero.
        try:
            validateTarget(term)

        except (TypeError, ValueError) as error:
            raise MalformedObservation(str(error)) from error

        if freeVariables(term):
            raise MalformedObservation('Cannot observe an open target term')
        value = observeValue(term, kind, state)
        return ObservationResult('completed', value, state.steps)

    except ObservationExhausted as error:
        # Report the consumed count, but discard any partially decoded components
        return ObservationResult('exhausted', None, state.steps, str(error))

    except MalformedObservation as error:
        # Distinguish an invalid data shape from a valid computation needing more steps
        return ObservationResult('malformed', None, state.steps, str(error))


def observeNatural(term: TargetTerm, budget: int) -> ObservationResult:
    return observe(term, 'nat', budget)


def observeBoolean(term: TargetTerm, budget: int) -> ObservationResult:
    return observe(term, 'bool', budget)


def observePair(term: TargetTerm, leftKind: Kind, rightKind: Kind,
                budget: int) -> ObservationResult:
    return observe(term, ('pair', leftKind, rightKind), budget)
