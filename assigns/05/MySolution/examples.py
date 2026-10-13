# shared example data, with fixed expected strings for both independent suites
from lambda1_vp import (
    D0Eint as I, 
    D0Ebtf as B, 
    D0Evar as V, 
    D0Eop1 as U, 
    D0Eop2 as O,
    D0Elam as L, 
    D0Efix as F, 
    D0Eapp as A, 
    D0Eif0 as C, 
    D0Elet as T,
    D0Epair as P, 
    D0Epfst as H, 
    D0Epsnd as S,
)

# tuples contain a label, an expression, and its literal expected output
# explicit expected examples verifying pretty printing
PRETTY_CASES = [
    ("integer", I(42), "42"),
    ("negative", I(-17), "-17"),
    ("large", I(10**40), "10000000000000000000000000000000000000000"),
    ("negative large", I(-(10**40)), "-10000000000000000000000000000000000000000"),
    ("true", B(True), "true"), ("false", B(False), "false"),
    ("variable", V("_name2"), "_name2"),
    ("unary", U("-1", V("x")), "(-1 x)"),
    ("binary", O("+", V("x"), I(1)), "(x + 1)"),
    ("lambda", L("x", V("x")), "(lam x. x)"),
    ("fix", F("f", "n", A(V("f"), V("n"))), "(fix f(n). (f n))"),
    ("application", A(V("f"), I(4)), "(f 4)"),
    ("conditional", C(B(True), I(1), I(2)), "(if true then 1 else 2)"),
    ("let", T("x", I(1), V("x")), "(let x = 1 in x)"),
    ("pair", P(I(1), B(False)), "(pair 1 false)"),
    ("first", H(V("p")), "(fst p)"), ("second", S(V("p")), "(snd p)"),
    ("nested", A(L("x", O("+", V("x"), I(1))), I(4)), "((lam x. (x + 1)) 4)"),
    ("division syntax", O("/", I(1), I(0)), "(1 / 0)"),
    ("nested projections", S(P(H(V("p")), I(-1))), "(snd (pair (fst p) -1))"),
]

# tuples contain label, input, target, replacement, and exact expected output
# explicit expected examples verifying substitution and scope
SUBSTITUTION_CASES = [
    ("integer", I(7), "x", I(3), "7"),
    ("boolean", B(False), "x", I(3), "false"),
    ("match", V("x"), "x", I(3), "3"),
    ("nonmatch", V("z"), "x", I(3), "z"),
    ("single insertion", V("x"), "x", O("+", V("x"), I(1)), "(x + 1)"),
    ("unary", U("odd", V("x")), "x", I(3), "(odd 3)"),
    ("binary", O("+", V("x"), V("x")), "x", I(3), "(3 + 3)"),
    ("lambda", L("z", V("x")), "x", I(3), "(lam z. 3)"),
    ("fix", F("f", "n", V("x")), "x", I(3), "(fix f(n). 3)"),
    ("application", A(V("x"), V("x")), "x", I(3), "(3 3)"),
    ("conditional", C(V("x"), V("x"), V("x")), "x", I(3), "(if 3 then 3 else 3)"),
    ("let", T("z", V("x"), V("x")), "x", I(3), "(let z = 3 in 3)"),
    ("pair", P(V("x"), V("x")), "x", I(3), "(pair 3 3)"),
    ("first", H(V("x")), "x", I(3), "(fst 3)"),
    ("second", S(V("x")), "x", I(3), "(snd 3)"),
    ("lambda shadows", L("x", O("+", V("x"), V("y"))), "x", I(3), "(lam x. (x + y))"),
    ("function shadows", F("x", "n", V("x")), "x", I(3), "(fix x(n). x)"),
    ("parameter shadows", F("f", "x", V("x")), "x", I(3), "(fix f(x). x)"),
    ("equal fix shadows", F("x", "x", V("x")), "x", I(3), "(fix x(x). x)"),
    ("let shadows body", T("x", V("x"), O("+", V("x"), V("y"))), "x", I(3), "(let x = 3 in (x + y))"),
    ("lambda capture", L("y", O("+", V("x"), V("y"))), "x", V("y"), "(lam y_1. (y + y_1))"),
    ("let capture", T("y", V("x"), O("+", V("x"), V("y"))), "x", V("y"), "(let y_1 = y in (y + y_1))"),
    ("initializer not renamed", T("y", V("y"), P(V("x"), V("y"))), "x", V("y"), "(let y_1 = y in (pair y y_1))"),
    ("function capture", F("f", "n", O("+", V("x"), A(V("f"), V("n")))), "x", V("f"), "(fix f_1(n). (f + (f_1 n)))"),
    ("parameter capture", F("f", "n", P(V("x"), A(V("f"), V("n")))), "x", V("n"), "(fix f(n_1). (pair n (f n_1)))"),
    ("both fix capture", F("f", "n", P(V("x"), A(V("f"), V("n")))), "x", P(V("f"), V("n")), "(fix f_1(n_1). (pair (pair f n) (f_1 n_1)))"),
    ("equal fix capture", F("f", "f", P(V("x"), V("f"))), "x", V("f"), "(fix f_1(f_1). (pair f f_1))"),
    ("nested lambda hides", L("y", P(V("x"), L("y", V("y")))), "x", V("y"), "(lam y_1. (pair y (lam y. y)))"),
    ("nested both rename", L("y", P(V("x"), L("y", P(V("x"), V("y"))))), "x", V("y"), "(lam y_1. (pair y (lam y_2. (pair y y_2))))"),
    ("nested let hides", L("y", P(V("x"), T("y", V("y"), V("y")))), "x", V("y"), "(lam y_1. (pair y (let y = y_1 in y)))"),
    ("nested function hides", L("y", P(V("x"), F("y", "n", P(V("y"), V("n"))))), "x", V("y"), "(lam y_1. (pair y (fix y(n). (pair y n))))"),
    ("nested parameter hides", L("y", P(V("x"), F("f", "y", V("y")))), "x", V("y"), "(lam y_1. (pair y (fix f(y). y)))"),
    ("original bound collision", L("y", P(V("x"), L("y_1", V("y")))), "x", V("y"), "(lam y_2. (pair y (lam y_1. y_2)))"),
    ("replacement bound collision", L("y", V("x")), "x", P(V("y"), L("y_1", I(0))), "(lam y_2. (pair y (lam y_1. 0)))"),
    ("target collision", L("y", V("y_1")), "y_1", V("y"), "(lam y_2. y)"),
    ("earlier generated collision", P(L("y", V("x")), L("y", V("x"))), "x", V("y"), "(pair (lam y_1. y) (lam y_2. y))"),
    ("absent lambda target", L("y", V("y")), "x", V("y"), "(lam y. y)"),
    ("absent fix target", F("f", "n", V("n")), "x", P(V("f"), V("n")), "(fix f(n). n)"),
    ("only initializer changes", T("y", V("x"), V("y")), "x", V("y"), "(let y = y in y)"),
    ("replacement bound name harmless", L("y", V("x")), "x", L("y", V("y")), "(lam y. (lam y. y))"),
    ("no input evaluation", O("/", V("x"), I(0)), "x", I(1), "(1 / 0)"),
    ("no replacement evaluation", V("x"), "x", O("/", I(1), I(0)), "(1 / 0)"),
    ("unused binder still captures", F("f", "n", V("x")), "x", V("n"), "(fix f(n_1). n)"),
    ("target bound prevents other renaming", F("x", "n", V("x")), "x", V("n"), "(fix x(n). x)"),
    ("shadowed target prevents renaming", L("y", L("x", V("x"))), "x", V("y"), "(lam y. (lam x. x))"),
]

# a dense body exercises the renaming traversal on every nonbinding constructor
# test renaming through every ordinary constructor.
SUBSTITUTION_CASES.append((
    "rename all ordinary forms",
    L("y", C(U("odd", V("y")), A(H(P(V("y"), B(False))), V("x")),
               S(P(I(2), O("+", V("y"), V("x")))))),
    "x", V("y"),
    "(lam y_1. (if (odd y_1) then ((fst (pair y_1 false)) y) else (snd (pair 2 (y_1 + y)))))",
))

# explicit expected free-variable sets complement the exact strings above
# check against independently specified free-variable sets
FV_CASES = [
    (O("+", V("x"), V("z")), "x", V("y"), {"y", "z"}),
    (L("y", P(V("x"), V("y"))), "x", V("y"), {"y"}),
    (T("x", V("x"), V("x")), "x", V("y"), {"y"}),
    (F("f", "n", V("x")), "x", P(V("f"), V("n")), {"f", "n"}),
    (V("x"), "x", O("+", V("x"), V("z")), {"x", "z"}),
    (L("x", P(V("x"), V("z"))), "x", V("y"), {"z"}),
    (V("z"), "x", V("y"), {"z"}),
]
