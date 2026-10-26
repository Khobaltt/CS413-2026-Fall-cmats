"""
Source-to-target compiler

Translate source expressions into pure lambda-calculus target terms
Compilation constructs syntax without evaluating the source or target
Conditionals and short-circuit operators use delayed lambda branches
Recursive functions use the expanded call-by-value Z combinator

Z is built here so church.py does not require an additional function
"""

from __future__ import annotations
from typing import TypeAlias

import lambda1_vp as source
import church
from target import Var, Lam, App, pretty, validateTarget
from scope import allNames


# TargetTerm is a type annotation, not an additional AST constructor
TargetTerm: TypeAlias = Var | Lam | App

# Each entry names a builder returning a closed, expanded target term
# Names here are Python function names, not target-language variables
UNARY_BUILDERS = {
    "not": "churchNot",
}

BINARY_BUILDERS = {
    "+": "churchAddition",
    "-": "churchSubtraction",
    "*": "churchMultiplication",
    "<": "churchLessThan",
    "<=": "churchLessEqual",
    ">": "churchGreaterThan",
    ">=": "churchGreaterEqual",
    "==": "churchEqual",
    "!=": "churchNotEqual",
}


def operatorTerm(operator: str, builders: dict[str, str]) -> TargetTerm:
    """
    Build the closed target combinator for a supported operator

    Raise ValueError for an unsupported spelling
    Raise NotImplementedError when a required step 9 builder is missing
    """

    if operator not in builders:
        raise ValueError(f"Unsupported operator: {operator!r}")

    builderName = builders[operator]
    builder = getattr(church, builderName, None)

    if builder is None:
        raise NotImplementedError(
            f"Operator {operator!r} requires church.{builderName}() from step 9; "
            "update the compiler table if your builder uses a different name"
        )

    # Calling a builder constructs syntax; it does not run the combinator
    return builder()


def callByValueZ() -> TargetTerm:
    """
    Z = lam f. (lam x. f (lam v. x x v))
               (lam x. f (lam v. x x v))

    Delay self-application beneath lam v until an argument is supplied
    Return a closed term containing only Var, Lam, and App nodes
    """

    # Build the delayed recursive call: lam v. ((x x) v)
    delayed = Lam('v', App(App(Var('x'), Var('x')), Var('v')))

    # Both halves are immutable target syntax and may safely share a subtree
    half = Lam('x', App(Var('f'), delayed))
    return Lam('f', App(half, half))


class Compiler(source.D0ExpVisitor[TargetTerm]):
    """Translate each source constructor through visitor dispatch"""

    def __init__(self) -> None:
        # Each compilation starts with the same deterministic name supply
        self.used: set[str] = set()
        self.counter = 0

    def freshName(self) -> str:
        """Return a deterministic identifier not already reserved"""

        while True:
            name = f"_thunk_{self.counter}"
            self.counter += 1

            if name not in self.used:
                self.used.add(name)
                return name

    def delayedConditional(
        self,
        condition: TargetTerm,
        thenBranch: TargetTerm,
        elseBranch: TargetTerm,
    ) -> TargetTerm:
        """
        Build (condition (lam u. thenBranch) (lam v. elseBranch)) I

        Reserve all names in the translated subterms before choosing binders
        This also protects free variables in open source expressions
        """

        self.used.update(allNames(condition))
        self.used.update(allNames(thenBranch))
        self.used.update(allNames(elseBranch))
        thenName = self.freshName()
        elseName = self.freshName()

        # Lambda bodies delay branch execution under call-by-value
        selected = App(
            App(condition, Lam(thenName, thenBranch)),
            Lam(elseName, elseBranch),
        )

        # Force only the selected thunk with the expanded identity value
        return App(selected, church.identity())

    def visit_int(self, expression: source.D0Eint) -> TargetTerm:
        """C[n] = NUM(n), for nonnegative integer literals"""

        # Reject negative literals and values that are not Python integers
        if type(expression.arg1) is not int or expression.arg1 < 0:
            raise ValueError(f"Unsupported natural literal: {expression.arg1!r}")

        return church.churchNatural(expression.arg1)

    def visit_btf(self, expression: source.D0Ebtf) -> TargetTerm:
        """C[true] = TRUE; C[false] = FALSE"""

        if type(expression.arg1) is not bool:
            raise ValueError(f"Invalid boolean literal: {expression.arg1!r}")

        if expression.arg1:
            return church.churchTrue()

        return church.churchFalse()

    def visit_var(self, expression: source.D0Evar) -> TargetTerm:
        """C[x] = x"""

        # Preserve free variables as well as bound variable references
        return Var(expression.arg1)

    def visit_lam(self, expression: source.D0Elam) -> TargetTerm:
        """C[lam x. body] = lam x. C[body]"""

        # Compile the body even though execution would delay it
        return Lam(expression.arg1, expression.arg2.accept(self))

    def visit_app(self, expression: source.D0Eapp) -> TargetTerm:
        """C[function argument] = C[function] C[argument]"""

        # Compile function first, then argument, without applying either
        function = expression.arg1.accept(self)
        argument = expression.arg2.accept(self)

        return App(function, argument)

    def visit_let(self, expression: source.D0Elet) -> TargetTerm:
        """C[let x = init in body] = (lam x. C[body]) C[init]"""

        initializer = expression.arg2.accept(self)
        body = expression.arg3.accept(self)

        # The new lambda surrounds only the body, not the initializer
        return App(Lam(expression.arg1, body), initializer)

    def visit_op1(self, expression: source.D0Eop1) -> TargetTerm:
        """C[not e] = NOT C[e]"""

        if expression.name not in UNARY_BUILDERS:
            raise ValueError(f"Unsupported unary operator: {expression.name!r}")

        operand = expression.arg1.accept(self)
        combinator = operatorTerm(expression.name, UNARY_BUILDERS)

        return App(combinator, operand)

    def visit_op2(self, expression: source.D0Eop2) -> TargetTerm:
        """C[left op right] = OP C[left] C[right] for strict operators"""

        if expression.name in ("and", "or"):
            # Compile BOTH operands, including syntax in a skipped operand
            left = expression.arg1.accept(self)
            right = expression.arg2.accept(self)

            if expression.name == "and":
                # left and right = if left then right else false
                return self.delayedConditional(left, right, church.churchFalse())

            # left or right = if left then true else right
            return self.delayedConditional(left, church.churchTrue(), right)

        if expression.name not in BINARY_BUILDERS:
            raise ValueError(f"Unsupported binary operator: {expression.name!r}")

        left = expression.arg1.accept(self)
        right = expression.arg2.accept(self)
        combinator = operatorTerm(expression.name, BINARY_BUILDERS)

        # Applications associate to the left: ((OP left) right)
        return App(App(combinator, left), right)

    def visit_pair(self, expression: source.D0Epair) -> TargetTerm:
        """C[pair left right] = PAIR C[left] C[right]"""

        left = expression.arg1.accept(self)
        right = expression.arg2.accept(self)

        # Target call-by-value evaluates both components before construction
        return App(App(church.churchPair(), left), right)

    def visit_pfst(self, expression: source.D0Epfst) -> TargetTerm:
        """C[fst e] = FIRST C[e]"""

        pair = expression.arg1.accept(self)
        return App(church.churchFirst(), pair)

    def visit_psnd(self, expression: source.D0Epsnd) -> TargetTerm:
        """C[snd e] = SECOND C[e]"""

        pair = expression.arg1.accept(self)
        return App(church.churchSecond(), pair)

    def visit_if0(self, expression: source.D0Eif0) -> TargetTerm:
        """C[if c then t else f] = (C[c] (lam u. C[t]) (lam v. C[f])) I"""

        # Compile condition and both branches without executing any of them
        condition = expression.arg1.accept(self)
        thenBranch = expression.arg2.accept(self)
        elseBranch = expression.arg3.accept(self)

        return self.delayedConditional(condition, thenBranch, elseBranch)

    def visit_fix(self, expression: source.D0Efix) -> TargetTerm:
        """C[fix f(x). body] = Z (lam f. lam x. C[body])"""

        body = expression.arg3.accept(self)

        # The parameter is the inner binder, so it shadows the function name
        # when both source names coincide
        definition = Lam(expression.arg1, Lam(expression.arg2, body))
        return App(callByValueZ(), definition)


def compile_expr(expression: source.D0E000) -> TargetTerm:
    """
    Translate a supported source AST into a pure target AST

    Accept open as well as closed source expressions
    Do not evaluate expressions or mutate the original source AST
    Validate all branches and function bodies, including unused expressions
    """

    if not isinstance(expression, source.D0E000):
        raise TypeError(f"Unsupported source node: {type(expression).__name__}")

    # Dispatch through the supplied source visitor interface
    term = expression.accept(Compiler())

    # Check the completed target tree, including identifier syntax
    validateTarget(term)
    return term


if __name__ == "__main__":
    # Running this file should print:
    # ((lam x. x) y)
    example = source.D0Eapp(
        source.D0Elam("x", source.D0Evar("x")),
        source.D0Evar("y"),
    )
    print(pretty(compile_expr(example)))
