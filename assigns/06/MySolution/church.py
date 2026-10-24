"""
Basic Church encoding builders

Every builder returns a pure target AST
Every completed combinator must be closed: freeVariables(term) == set()

Names such as TRUE and PAIR are documentation abbreviations
Generated terms must contain their expanded lambda expressions
"""

from __future__ import annotations

from target import Var, Lam, App


TargetTerm = Var | Lam | App


def identity() -> TargetTerm:
    """
    I = lam(x). x

    Returns its argument unchanged
    """

    # Build a lambda whose body refers to its parameter
    return Lam('x', Var('x'))

def churchTrue() -> TargetTerm:
    """
    TRUE = lam(t). lam(f). t
    Selects the first of two arguments
    """
    return Lam('t', Lam('f', Var('t')))

def churchFalse() -> TargetTerm:
    """
    FALSE = lam(t). lam(f). f
    Selects the second of two arguments
    """
    return Lam('t', Lam('f', Var('f')))

def churchNatural(number: int) -> TargetTerm:
    """
    Encode a nonnegative integer as a Church numeral
    Repeatedly apply a function f to a variable x
    churchNatural(3) -> lam(f). lam(x). f (f (f x))
    """

    # Check that number is a nonnegative integer
    if type(number) is not int or number < 0:
        raise ValueError("Number must be a nonnegative integer")

    # Start the body
    temp = Var('x')

    # Wrap the body in App() number times
    for _ in range(number):
        temp = App(Var('f'), temp)

    # Wrap the finished body in lam(f). lam(x).
    return Lam('f', Lam('x', temp))

def churchPair() -> TargetTerm:
    """
    PAIR = lam(a). lam(b). lam(s). s a b

    Applications associate to the left:
        s a b = ((s a) b)

    Applying PAIR to two values returns a value that passes both components to a selector
    """

    # Build ((s a) b) using two App nodes.
    body = App(App(Var('s'), Var('a')), Var('b'))

    # Wrap the body in lambdas for a, b, and s
    return Lam('a', Lam('b', Lam('s', body)))

def churchFirst() -> TargetTerm:
    """
    FIRST = λp. p TRUE
    Selects a pair's first component
    """

    # Apply p to the expanded result of churchTrue()
    body = App(Var('p'), churchTrue())

    # Wrap the application in lam(p)
    return Lam('p', body)

def churchSecond() -> TargetTerm:
    """
    SECOND = λp. p FALSE
    Selects a pair's second component
    """

    # Apply p to the expanded result of churchFalse()
    body = App(Var('p'), churchFalse())

    # Wrap the application in lam(p)
    return Lam('p', body)

def churchSuccessor() -> TargetTerm:
    """
    SUCC = λn. λf. λx. f (n f x)

    Applies f once more than the numeral n does
    """

    # Build ((n f) x)
    init = App(App(Var('n'), Var('f')), Var('x'))

    # Apply f to that expression
    succ = App(Var('f'), init)

    # Wrap the body in lambdas for n, f, and x
    return Lam('n', Lam('f', Lam('x', succ)))
