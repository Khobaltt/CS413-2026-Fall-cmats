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


# ------------------------------------------------------------------
# Natural-number operations
# ------------------------------------------------------------------

def churchPredecessor() -> TargetTerm:
    """
    PRED n = max(n - 1, 0)

    Use pairs to track the previous and current numbers:
        (a, b) -> (b, b + 1)

    Starting with (0, 0):
        0 iterations -> (0, 0)
        1 iteration  -> (0, 1)
        2 iterations -> (1, 2)

    Return the first component after n iterations.
    """

    # Build SECOND p using churchSecond()
    sec = App(churchSecond(), Var('p'))

    # Build SUCC (SECOND p) using churchSuccessor()
    succ = App(churchSuccessor(), sec)

    # Build the transition:
    # lam(p). PAIR (SECOND p) (SUCC (SECOND p))
    trans = Lam('p', App(App(churchPair(), sec), succ))

    # Build the initial pair: PAIR NUM(0) NUM(0)
    init = App(App(churchPair(), churchNatural(0)), churchNatural(0))

    # Build the iteration: n TRANSITION INITIAL_PAIR
    iteration = App(App(Var('n'), trans), init)

    # Apply FIRST to the iteration result
    first = App(churchFirst(), iteration)

    # Wrap the expression in lam(n)
    return Lam('n', first)


def churchIsZero() -> TargetTerm:
    """
    ISZERO = lam(n). n (lam(ignored). FALSE) TRUE

    Zero returns the starting TRUE
    A positive numeral applies the function and returns FALSE
    """

    temp = App(Var('n'), Lam('ignored', churchFalse()))

    return Lam('n', App(temp, churchTrue()))


def churchAddition() -> TargetTerm:
    """
    ADD = lam(m). lam(n). lam(f). lam(x). m f (n f x)

    Apply f n times, then apply it m more times
    """

    # Build ((n f) x)
    temp = App(App(Var('n'), Var('f')), Var('x'))

    # Build ((m f) INNER_RESULT)
    temp = App(App(Var('m'), Var('f')), temp)

    # Wrap the body in lambdas for m, n, f, and x.
    return Lam('m', Lam('n', Lam('f', Lam('x', temp))))


def churchSubtraction() -> TargetTerm:
    """
    SUB = lam(m). lam(n). n PRED m

    Apply predecessor n times to m
    Because PRED zero is zero, subtraction truncates at zero
    """

    # Build ((n PRED) m), expanding churchPredecessor()
    temp = App(App(Var('n'), churchPredecessor()), Var('m'))

    # Wrap the expression in lambdas for m and n
    # Both operands are bound here, so the completed combinator remains closed
    return Lam('m', Lam('n', temp))


def churchMultiplication() -> TargetTerm:
    """
    MUL = lam(m). lam(n). lam(f). lam(x). m (n f) x

    Repeat the operation "apply f n times" a total of m times
    """

    # Build (n f)
    temp = App(Var('n'), Var('f'))

    # Build ((m INNER_RESULT) x)
    temp = App(App(Var('m'), temp), Var('x'))

    # Wrap the body in lambdas for m, n, f, and x.
    return Lam('m', Lam('n', Lam('f', Lam('x', temp))))


# ------------------------------------------------------------------
# Boolean operations
# ------------------------------------------------------------------

def churchNot() -> TargetTerm:
    """
    NOT = lam(p). p FALSE TRUE
    """

    # Build ((p FALSE) TRUE)
    temp = App(App(Var('p'), churchFalse()), churchTrue())

    # Wrap the expression in lam(p)
    return Lam('p', temp)


def churchAnd() -> TargetTerm:
    """
    AND = lam(p). lam(q). p q FALSE

    Accepts two encoded boolean values
    """

    # Build ((p q) FALSE), expanding churchFalse()
    temp = App(App(Var('p'), Var('q')), churchFalse())

    # Wrap the expression in lambdas for p and q
    return Lam('p', Lam('q', temp))


def churchOr() -> TargetTerm:
    """
    OR = lam(p). lam(q). p TRUE q

    Accepts two encoded boolean values
    """

    # Build ((p TRUE) q), expanding churchTrue()
    temp = App(App(Var('p'), churchTrue()), Var('q'))

    # Wrap the expression in lambdas for p and q
    return Lam('p', Lam('q', temp))


# ------------------------------------------------------------------
# Natural-number comparisons
# ------------------------------------------------------------------

def churchLessEqual() -> TargetTerm:
    """
    LEQ = lam(m). lam(n). ISZERO (SUB m n)

    m <= n exactly when truncated m - n is zero
    """

    # Build SUB m n using churchSubtraction()
    temp = App(App(churchSubtraction(), Var('m')), Var('n'))

    # Apply churchIsZero() to that expression
    temp = App(churchIsZero(), temp)

    # Wrap the expression in lambdas for m and n
    return Lam('m', Lam('n', temp))


def churchGreaterEqual() -> TargetTerm:
    """
    GEQ = lam(m). lam(n). LEQ n m
    """

    # Apply churchLessEqual() to n, then m
    temp = App(App(churchLessEqual(), Var('n')), Var('m'))

    # Wrap the expression in lambdas for m and n
    return Lam('m', Lam('n', temp))


def churchLessThan() -> TargetTerm:
    """
    LT = lam(m). lam(n). NOT (LEQ n m)

    m < n exactly when n <= m is false
    """

    # Build LEQ n m
    temp = App(App(churchLessEqual(), Var('n')), Var('m'))

    # Apply churchNot() to the comparison
    temp = App(churchNot(), temp)

    # Wrap the expression in lambdas for m and n
    return Lam('m', Lam('n', temp))


def churchGreaterThan() -> TargetTerm:
    """
    GT = lam(m). lam(n). NOT (LEQ m n)
    """

    # Build LEQ m n
    temp = App(App(churchLessEqual(), Var('m')), Var('n'))

    # Apply churchNot() to the comparison
    temp = App(churchNot(), temp)

    # Wrap the expression in lambdas for m and n
    return Lam('m', Lam('n', temp))


def churchEqual() -> TargetTerm:
    """
    EQ = lam(m). lam(n). AND (LEQ m n) (LEQ n m)
    """

    # Build LEQ m n
    temp = App(App(churchLessEqual(), Var('m')), Var('n'))

    # Build LEQ n m
    temp2 = App(App(churchLessEqual(), Var('n')), Var('m'))

    # Apply churchAnd() to both comparisons
    temp = App(App(churchAnd(), temp), temp2)

    # Wrap the expression in lambdas for m and n
    return Lam('m', Lam('n', temp))


def churchNotEqual() -> TargetTerm:
    """
    NEQ = lam(m). lam(n). NOT (EQ m n)
    """

    # Build EQ m n using churchEqual()
    temp = App(App(churchEqual(), Var('m')), Var('n'))

    # Apply churchNot() to that expression
    temp = App(churchNot(), temp)

    # Wrap the expression in lambdas for m and n
    return Lam('m', Lam('n', temp))
