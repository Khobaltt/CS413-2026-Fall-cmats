"""
Target free variable analysis, target all-name collection, and deterministic, fresh-name generator

"""

from __future__ import annotations

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
Fresh name generator must be initialized once per substitution

Example: substitute x:=y into lam(y).x
Reserved names: {x, y}
fresh.new("y"): y_1
Result:         lam(y_1). y
"""

def _renameBound(body: object, oldName: str, newName: str):
    """
    Rename occurrences bound by an enclosing binder being renamed.

    The caller changes that enclosing declaration separately and passes
    ONLY its body here. newName must be fresh for all relevant terms.
    A nested lambda declaring oldName shadows the enclosing binder, so
    neither that nested declaration nor its body should be changed.
    """

    if type(body) is Var:
        # If body.name == oldName, return Var(newName)
        # Otherwise return body unchanged
        if body.name == oldName:
            return Var(newName)
        else:
            return body

    if type(body) is App:
        # Recursively rename the function, then the argument
        # Return a new App containing the two results
        return App(
            _renameBound(body.function, oldName, newName),
            _renameBound(body.argument, oldName, newName)
        )

    if type(body) is Lam:
        # If body.name == oldName, return body unchanged
        # Otherwise preserve body.name, recursively rename body.body
        # Return a Lam
        if body.name == oldName:
            return body
        else:
            return Lam(body.name, _renameBound(body.body, oldName, newName))

    raise TypeError(f"Unsupported target node: {type(body).__name__}")


def _substitute(term: object, variable: str, replacement: object, replacementFree: set[str], fresh: FreshNames):
    """
    Recursive worker; every recursive call shares the same fresh supply
    """

    if type(term) is Var:
        # Return replacement if term.name == variable
        # Otherwise return term unchanged
        if term.name == variable:
            return replacement
        else:
            return term

    if type(term) is App:
        # Recursively substitute in term.function first, then term.argument, passing all the same context arguments
        # Return a new App with the transformed children
        return App(
            _substitute(term.function, variable, replacement, replacementFree, fresh), 
            _substitute(term.argument, variable, replacement, replacementFree, fresh)
        )

    if type(term) is Lam:
        # Handle 4 cases:

        # 1: The lambda binds the variable being replaced, so occurrencesbeneath this binder are not free occurrences of that variable
        # Return the term unchanged
        if term.name == variable:
            return term
        
        # 2: No free variable to replace in the body
        # Return the term unchanged
        elif variable not in freeVariables(term.body):
            return term

        # 3: Substitution is needed, and the binder cannot capture the replacement
        # Return a Lam with the same binder and recursively substituded body
        elif term.name not in replacementFree:
            return Lam(
                term.name,
                _substitute(term.body, variable, replacement, replacementFree, fresh)
            )

        # 4: Substitution is needed, and the binder would capture the replacement
        # Return a Lam
        else:
            newName = fresh.new(term.name)
            renamedBody = _renameBound(term.body, term.name, newName)
            substitutedBody = _substitute(renamedBody, variable, replacement, replacementFree, fresh)
            return Lam(newName, substitutedBody)

    raise TypeError(f"Unsupported target node: {type(term).__name__}")


def substitute(term: object, variable: str, replacement: object):
    """
    Return term with its free occurrences of variable replaced

    Inputs must be valid target ASTs with valid identifier strings
    Original nodes and the replacement must remain unchanged
    """

    # Reserve allNames(term), allNames(replacement), and {variable}
    reserved = allNames(term) | allNames(replacement) | {variable}
    
    # Create FreshNames(reserved) ONCE for this public call
    fresh = FreshNames(reserved)

    # Compute freeVariables(replacement) once
    replacementFree = freeVariables(replacement)

    # Return _substitute(term, variable, replacement, replacementFree, fresh)
    return _substitute(term, variable, replacement, replacementFree, fresh)

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