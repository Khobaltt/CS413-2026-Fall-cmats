# import from supplied visitor-based implementation
from .. import lambda1_vp
from lambda1_vp import (
    D0ExpVisitor, 
    d0exp, 
    d0exp_fvset, 
    D0Eint, 
    D0Ebtf, 
    D0Evar, 
    D0Eop1, 
    D0Eop2, 
    D0Elam, 
    D0Efix, 
    D0Eapp, 
    D0Eif0, 
    D0Elet, 
    D0Epair, 
    D0Epfst, 
    D0Epsnd
)

# turn syntax into text, without running any of its operations
class PrettyPrintVisitor(D0ExpVisitor[str]):

    # str on a Python integer gives decimal digits, even for huge values
    def visit_int(self, e):
        return str(e.arg1)

    # the assignment uses lowercase booleans rather than Python spelling
    def visit_btf(self, e):
        return "true" if e.arg1 else "false"

    # names are printed literally, not looked up in an environment
    def visit_var(self, e):
        return e.arg1

    # each child chooses its own visitor method through accept
    def visit_op1(self, e):
        return f"({e.name} {e.arg1.accept(self)})"

    # printing an operator never applies it, including division by zero
    def visit_op2(self, e):
        return f"({e.arg1.accept(self)} {e.name} {e.arg2.accept(self)})"

    # lambda's first argument is a name, second is its body
    def visit_lam(self, e):
        return f"(lam {e.arg1}. {e.arg2.accept(self)})"

    # a fix stores its function name, parameter name, then body
    def visit_fix(self, e):
        return f"(fix {e.arg1}({e.arg2}). {e.arg3.accept(self)})"

    # application is displayed as two expressions inside parentheses
    def visit_app(self, e):
        return f"({e.arg1.accept(self)} {e.arg2.accept(self)})"

    # print all three children, regardless of the condition's value
    def visit_if0(self, e):
        return (f"(if {e.arg1.accept(self)} then {e.arg2.accept(self)} " f"else {e.arg3.accept(self)})")

    # initializer and body are separate expression children
    def visit_let(self, e):
        return f"(let {e.arg1} = {e.arg2.accept(self)} in {e.arg3.accept(self)})"

    # preserve both members of the pair in their original order
    def visit_pair(self, e):
        return f"(pair {e.arg1.accept(self)} {e.arg2.accept(self)})"

    # display the projection; do not extract a value from a pair
    def visit_pfst(self, e):
        return f"(fst {e.arg1.accept(self)})"

    # this is the second projection's syntax, not an evaluated result
    def visit_psnd(self, e):
        return f"(snd {e.arg1.accept(self)})"

# public entry point: use a fresh printing visitor for this expression
def d0exp_pretty(expression: d0exp) -> str:
    return expression.accept(PrettyPrintVisitor())