"""
Pure lambda-calculus target AST and printer scaffold.

Only variables, lambdas, and applications belong in this AST.
Evaluation, substitution, and Church encodings go in separate files.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TypeAlias

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
# Future annotations allow the classes above to refer to this alias
Term: TypeAlias = Var | Lam | App

def pretty(term: Term) -> str:
    """
    Return the required fully parenthesized target notation
    Reference:
    Var("x")                          -> "x"
    Lam("x", Var("x"))                -> "(lam x. x)"
    App(Lam("x", Var("x")), Var("y")) -> "((lam x. x) y)"

    Printing must describe the tree without evaluating or modifying it
    """
    if isinstance(term, Var):
        # Print variable directly
        return term.name

    if isinstance(term, Lam):
        # Recursively print term.body
        # Combine it with term.name using exactly: (lam name. body)
        return f"(lam {term.name}. {pretty(term.body)})"

    if isinstance(term, App):
        # Recursively print term.function and term.argument
        # Combine them with a space and surrounding parentheses: (fn arg)
        return f"({pretty(term.function)} {pretty(term.argument)})"

    raise TypeError(f"Unsupported target node: {type(term).__name__}")

def validateTarget(term: object) -> None:
    """
    Check target syntax recursively 

    Return None when the entire tree is valid
    Raise TypeError for an unsupported node
    Raise ValueError for a bad name
    
    Free variables are considered valid syntax
    """
    
    # Do not reserve names such as PLUS: they may be legitimate variables.

    def validateName(name: object) -> None:

        # check that name is a string
        if not isinstance(name, str):
            raise ValueError("")

        # TODO: check that name follows identifier policy
        #
        #
        #
        #

    # Var: check name
    if type(term) is Var:
        validateName(term.name)
        return

    # Lam: check name, then recursively validate body
    if type(term) is Lam:
        validateName(term.name)
        validateTarget(term.body)
        return

    # App: recursively validate both function and argument
    if type(term) is App:
        validateTarget(term.function)
        validateTarget(term.argument)
        return

    # reject all other types
    raise TypeError(f"Unsupported target node: {type(term).__name__}")


if __name__ == "__main__":
    # Running this file should print:
    # ((lam x. x) y)
    example = App(Lam("x", Var("x")), Var("y"))
    print(pretty(example))
