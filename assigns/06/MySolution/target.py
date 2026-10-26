"""
Pure lambda-calculus target AST and printer.

Only variables, lambdas, and applications belong in this AST.
Evaluation, substitution, and Church encodings go in separate files.
Target traversal uses explicit stacks rather than Python recursion.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TypeAlias
import re


@dataclass(frozen=True)
class Var:
    """A variable reference: x"""

    name: str


@dataclass(frozen=True)
class Lam:
    """A function with one parameter: (lam x. body)"""

    name: str
    body: Term


@dataclass(frozen=True)
class App:
    """A function applied to one argument: (fn arg)"""

    function: Term
    argument: Term


# Term is a type annotation, not an additional AST constructor
Term: TypeAlias = Var | Lam | App


def pretty(term: Term) -> str:
    """
    Return the required fully parenthesized notation without evaluating.

    Var("x")                          -> "x"
    Lam("x", Var("x"))                -> "(lam x. x)"
    App(Lam("x", Var("x")), Var("y")) -> "((lam x. x) y)"
    """

    # Accumulate text fragments, then join them once after the traversal
    pieces = []
    # A term action visits syntax; a text action writes saved punctuation
    pending = [('term', term)]

    while pending:

        action, current = pending.pop()

        if action == 'text':
            # Write punctuation after the preceding child has finished
            pieces.append(current)

        elif type(current) is Var:
            # Print the variable name directly
            pieces.append(current.name)

        elif type(current) is Lam:
            # Print the opening lambda, then its body, then the saved closing parenthesis
            pieces.append(f'(lam {current.name}. ')
            pending.append(('text', ')'))
            pending.append(('term', current.body))

        elif type(current) is App:
            # Print (function argument), preserving both the space and parentheses
            pieces.append('(')
            # Push in reverse order so the function prints first.
            pending.append(('text', ')'))
            pending.append(('term', current.argument))
            pending.append(('text', ' '))
            pending.append(('term', current.function))

        else:
            raise TypeError(f'Unsupported target node: {type(current).__name__}')
    # Printing constructs text only; it never evaluates or changes the AST
    return ''.join(pieces)


def validateTarget(term: object) -> None:
    """
    Check pure target syntax and identifier names using an explicit stack.

    Return None for valid syntax, including open terms. Raise TypeError for
    unsupported nodes and ValueError for invalid names.
    """

    # Keep the nodes that still need structural validation
    pending = [term]

    while pending:

        current = pending.pop()

        if type(current) in (Var, Lam):
            # Variables and lambda binders follow the same identifier policy
            name = current.name
            # Reject non-string names before applying the identifier expression
            if not isinstance(name, str):
                raise ValueError(f'Expected a string, got {name!r}')
            # Names such as PLUS remain valid; encoding abbreviations are not reserved
            if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) is None:
                raise ValueError(f'Invalid identifier: {name!r}')

            if type(current) is Lam:
                # The binder is valid; continue checking the body
                pending.append(current.body)

        elif type(current) is App:
            # Validate both children, visiting the function before the argument
            pending.append(current.argument)
            pending.append(current.function)

        else:
            raise TypeError(f'Unsupported target node: {type(current).__name__}')


if __name__ == '__main__':
    # Running this file should print: ((lam x. x) y)
    example = App(Lam('x', Var('x')), Var('y'))
    print(pretty(example))
