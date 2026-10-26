"""
All fourteen required source AST demonstrations: DEM-01, DEM-02

Expected answers are explicit constants, never computed by the compiler.
LOOP cases must run only through bounded target execution.
"""

from dataclasses import dataclass

import lambda1_vp as source
from observers import Kind


@dataclass(frozen=True)
class Example:
    identifier: str
    title: str
    expression: source.D0E000
    kind: Kind | None
    expected: object
    executionBudget: int = 10000
    observationBudget: int = 10000

    @property
    def expectsExhaustion(self) -> bool:
        return self.kind is None


def loopExpression():
    """LOOP = (fix loop(x). loop x) 0; build fresh syntax each time."""
    return source.D0Eapp(
        source.D0Efix('loop', 'x', source.D0Eapp(
            source.D0Evar('loop'), source.D0Evar('x'))),
        source.D0Eint(0),
    )


def factorialExpression(number=4):
    return source.D0Eapp(source.D0Efix('fact', 'n', source.D0Eif0(
        source.D0Eop2('==', source.D0Evar('n'), source.D0Eint(0)),
        source.D0Eint(1),
        source.D0Eop2('*', source.D0Evar('n'), source.D0Eapp(
            source.D0Evar('fact'),
            source.D0Eop2('-', source.D0Evar('n'), source.D0Eint(1)))),
    )), source.D0Eint(number))


def fibonacciExpression(number=5):
    return source.D0Eapp(source.D0Efix('fib', 'n', source.D0Eif0(
        source.D0Eop2('<=', source.D0Evar('n'), source.D0Eint(1)),
        source.D0Evar('n'),
        source.D0Eop2('+',
            source.D0Eapp(source.D0Evar('fib'), source.D0Eop2(
                '-', source.D0Evar('n'), source.D0Eint(1))),
            source.D0Eapp(source.D0Evar('fib'), source.D0Eop2(
                '-', source.D0Evar('n'), source.D0Eint(2)))),
    )), source.D0Eint(number))


def requiredExamples() -> tuple[Example, ...]:
    """Return fresh source trees in the REQUIREMENTS.md DEMO-01–14 order."""
    N, B, V = source.D0Eint, source.D0Ebtf, source.D0Evar
    return (
        Example('DEMO-01', '2 + 3 * 4',
                source.D0Eop2('+', N(2), source.D0Eop2('*', N(3), N(4))), 'nat', 14),
        Example('DEMO-02', '2 - 5', source.D0Eop2('-', N(2), N(5)), 'nat', 0),
        Example('DEMO-03', 'if 2 <= 3 then 7 else 9', source.D0Eif0(
            source.D0Eop2('<=', N(2), N(3)), N(7), N(9)), 'nat', 7),
        Example('DEMO-04', 'let x = 3 in (lam y. x + y) 4', source.D0Elet(
            'x', N(3), source.D0Eapp(source.D0Elam('y',
                source.D0Eop2('+', V('x'), V('y'))), N(4))), 'nat', 7),
        Example('DEMO-05', 'fst (pair 2 true)',
                source.D0Epfst(source.D0Epair(N(2), B(True))), 'nat', 2),
        Example('DEMO-06', 'snd (pair 2 true)',
                source.D0Epsnd(source.D0Epair(N(2), B(True))), 'bool', True),
        Example('DEMO-07', '(lam f. f 3) (lam x. x + 1)', source.D0Eapp(
            source.D0Elam('f', source.D0Eapp(V('f'), N(3))),
            source.D0Elam('x', source.D0Eop2('+', V('x'), N(1)))), 'nat', 4),
        Example('DEMO-08', 'if true then 1 else LOOP',
                source.D0Eif0(B(True), N(1), loopExpression()), 'nat', 1),
        Example('DEMO-09', '(lam x. 0) LOOP',
                source.D0Eapp(source.D0Elam('x', N(0)), loopExpression()),
                None, 'step-budget exhaustion', 200),
        Example('DEMO-10', 'factorial 4', factorialExpression(), 'nat', 24),
        Example('DEMO-11', 'Fibonacci 5', fibonacciExpression(), 'nat', 5),
        Example('DEMO-12', 'LOOP', loopExpression(),
                None, 'step-budget exhaustion', 200),
        Example('DEMO-13', 'true and false',
                source.D0Eop2('and', B(True), B(False)), 'bool', False),
        Example('DEMO-14', 'false or true',
                source.D0Eop2('or', B(False), B(True)), 'bool', True),
    )
