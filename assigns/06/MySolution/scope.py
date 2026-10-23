"""
Target free variable analysis, target all-name collection, and deterministic, fresh-name generator

"""

from target import Var, Lam, App
from visitors import FreshNames

def freeVariables(term: object) -> set[str]:
    """
    Return the set of free variables in the target AST

    Var(name)               -> {name}
    Lam(name, body)         -> FV(body) - {name}
    App(function, argument) -> FV(function) U FV(argument)

    Raise TypeError for unsupported nodes
    """

    if type(term) is Var:
        # return a set with only the term name
        return {term.name}

    if type(term) is Lam:
        # return the set of free variables in the term body, excluding the term name
        return freeVariables(term.body) - {term.name}

    if type(term) is App:
        # return the union of free variables in the term function and term argument
        return freeVariables(term.function) | freeVariables(term.argument)

    raise TypeError(f"Unsupported target node: {type(term).__name__}")

def allNames(term: object) -> set[str]:
    """
    Returns the set of all variable names and binder declarations, including unused binders

    Var(name)               -> {name}
    Lam(name, body)         -> {name} U AN(body)
    App(function, argument) -> AN(function) U AN(argument)

    Raise TypeError for unsupported nodes
    """

    if type(term) is Var:
        # return a set with only the term name
        return {term.name}

    if type(term) is Lam:
        # return the set containing the term name and term body's names
        return {term.name} | allNames(term.body)

    if type(term) is App:
        # return the union of all names in the term function and term argument
        return allNames(term.function) | allNames(term.argument)

    raise TypeError(f"Unsupported target node: {type(term).__name__}")

"""
Reusing the existing fresh-name policy from assign05:

For each requested base, try base_1, base_2, and so on, skipping every reserved or previously generated name

Maintains:
self.used     -> all names the generator must avoid
self.counters -> the last accepted suffix for each base

Suffixes are always added, even when a name without a suffix is available
The used name set is shared across all bases
The generator does not try to interpret existing suffixes

Fresh name generator must be initialized once per substitution:
# reserve every name in both terms and the variable being replaced
reserved = allNames(term) | allNames(replacement) | {variable}
# create one supply shared by this entire substitution
fresh = FreshNames(reserved)
# pass fresh to the recursive substitution helper
newName = fresh.new(term.name)

Example: substitute x:=y into lam(y).x
Reserved names: {x, y}
fresh.new("y"): y_1
Result:         lam(y_1). y
"""

if __name__ == "__main__":
    # running this file should print:
    #
    # set()
    # {'y'}
    # {'y'}
    # {'x'}
    # {'y', 'x'}
    # {'y', 'x'}
    # x_2
    #
    example1 = Lam("x", Var("x"))
    example2 = Lam("x", Var("y"))
    example3 = App(Lam("x", Var("x")), Var("y"))
    print(freeVariables(example1))
    print(freeVariables(example2))
    print(freeVariables(example3))
    print(allNames(example1))
    print(allNames(example2))
    print(allNames(example3))
    print(FreshNames({"x_1"}).new("x"))