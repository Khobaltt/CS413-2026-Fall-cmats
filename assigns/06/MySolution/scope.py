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

    # Collect free names and count the active binders for each name
    # Counts preserve an outer binding when an inner binding uses the same name
    result = set()
    bound = {}

    # pending is a stack: the most recently added action runs first
    pending = [('visit', term)]

    while pending:

        action, current = pending.pop()

        if action == 'leave':
            # The lambda body is finished, so remove this binder from the active scope
            bound[current] -= 1

            # Keep the name active if an outer lambda still binds it
            if bound[current] == 0:
                del bound[current]

        elif type(current) is Var:
            # A variable is free only when no active lambda binds its name
            if current.name not in bound:
                result.add(current.name)

        elif type(current) is Lam:
            # Activate the binder before visiting the body
            bound[current.name] = bound.get(current.name, 0) + 1

            # Visit the body first, then leave its binding scope
            pending.append(('leave', current.name))
            pending.append(('visit', current.body))

        elif type(current) is App:
            # Push argument before function so the function is visited first
            # Each child's lambda bindings are removed before visiting its sibling
            pending.append(('visit', current.argument))
            pending.append(('visit', current.function))

        else:
            raise TypeError(f'Unsupported target node: {type(current).__name__}')

    return result

def allNames(term: object) -> set[str]:
    """
    Returns the set of all variable names and binder declarations, including unused binders

    Var(name)               -> {name}
    Lam(name, body)         -> {name} U AN(body)
    App(function, argument) -> AN(function) U AN(argument)

    Raise TypeError for unsupported nodes
    """

    result = set()
    pending = [term]

    while pending:

        current = pending.pop()

        if type(current) is Var:
            # Keep every variable occurrence, whether it is free or bound
            result.add(current.name)

        elif type(current) is Lam:
            # Include the binder even when its body never refers to it
            result.add(current.name)
            pending.append(current.body)

        elif type(current) is App:
            # Visit the function before the argument
            pending.append(current.argument)
            pending.append(current.function)

        else:
            raise TypeError(f'Unsupported target node: {type(current).__name__}')

    return result

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
    Rename occurrences bound by an enclosing binder being renamed

    The caller changes that enclosing declaration separately and passes
    ONLY its body here. newName must be fresh for all relevant terms.
    A nested lambda declaring oldName shadows the enclosing binder, so
    neither that nested declaration nor its body should be changed.
    """

    # pending stores visits and rebuild actions
    # values stores finished subtrees until their parent can be rebuilt
    pending = [('visit', body)]
    values = []

    while pending:

        action, current = pending.pop()

        if action == 'lam':
            # The renamed body is ready; wrap it in the original lambda binder
            values.append(Lam(current.name, values.pop()))

        elif action == 'app':
            # Function was visited first, so argument is the most recent result
            argument = values.pop()
            function = values.pop()
            values.append(App(function, argument))

        elif type(current) is Var:
            # Rename only occurrences of the enclosing binder's old name
            values.append(Var(newName) if current.name == oldName else current)

        elif type(current) is Lam:

            if current.name == oldName:
                # This lambda shadows the enclosing binder; preserve its entire subtree
                values.append(current)

            else:
                # Rename the body before rebuilding the lambda
                pending.append(('lam', current))
                pending.append(('visit', current.body))

        elif type(current) is App:
            # Finish function and argument before rebuilding their application
            pending.append(('app', current))
            pending.append(('visit', current.argument))
            pending.append(('visit', current.function))

        else:
            raise TypeError(f'Unsupported target node: {type(current).__name__}')

    # The final result is the rebuilt root, with both inputs left unchanged
    return values.pop()

def _containsFree(term, variable, cache):
    """
    Cache whether a subtree contains variable free, without recursive calls

    Retain node references alongside their IDs so temporary renamed trees
    cannot be confused if Python later reuses an object ID.

    ready=False -> visit the children before computing this node's result
    ready=True  -> use the children's cached results
    """

    pending = [(term, False)]

    while pending:

        current, ready = pending.pop()
        key = id(current)

        if key in cache:
            # Reuse results for shared or previously visited subtrees
            continue

        if type(current) is Var:
            # A matching variable is free within this one-node subtree
            cache[key] = (current, current.name == variable)

        elif type(current) is Lam:

            if current.name == variable:
                # This lambda binds every matching occurrence that could be free in its body
                cache[key] = (current, False)

            elif ready:
                # A different binder does not change whether variable is free
                cache[key] = (current, cache[id(current.body)][1])

            else:
                # Save this lambda until its body has a cached answer
                pending.append((current, True))
                pending.append((current.body, False))

        elif type(current) is App:

            if ready:
                # The name is free in an application if it is free in either child
                cache[key] = (current, cache[id(current.function)][1]
                              or cache[id(current.argument)][1])

            else:
                # Visit both children before combining their cached answers
                pending.append((current, True))
                pending.append((current.argument, False))
                pending.append((current.function, False))

        else:
            raise TypeError(f'Unsupported target node: {type(current).__name__}')

    return cache[id(term)][1]

def _substitute(term: object, variable: str, replacement: object, replacementFree: set[str], fresh: FreshNames):
    """
    Iterative worker; every visit shares the same fresh supply

    Visit subtrees using pending, then rebuild their parents using values
    Cache free-occurrence checks to avoid rescanning unchanged subtrees
    """

    pending = [('visit', term)]
    values = []
    containsFree = {}

    while pending:

        action, current = pending.pop()

        if action == 'lam':
            # current stores the binder name chosen before visiting this body
            values.append(Lam(current, values.pop()))

        elif action == 'app':
            # Restore the original function/argument order when rebuilding
            argument = values.pop()
            function = values.pop()
            values.append(App(function, argument))

        elif type(current) is Var:
            # Insert replacement only at matching free occurrences
            # Do not traverse replacement or substitute inside it again
            values.append(replacement if current.name == variable else current)

        elif type(current) is App:
            # Visit function first, then argument, sharing one fresh-name generator
            pending.append(('app', None))
            pending.append(('visit', current.argument))
            pending.append(('visit', current.function))

        elif type(current) is Lam:

            # Stop when the binder shadows variable or the body contains nothing to replace
            # Neither case needs a fresh name or a rebuilt lambda
            if current.name == variable or not _containsFree(current.body, variable, containsFree):
                values.append(current)
                continue

            name = current.name
            body = current.body

            if name in replacementFree:
                # This binder would capture a free name in replacement
                # Rename its bound occurrences before inserting replacement
                name = fresh.new(name)
                body = _renameBound(body, current.name, name)

            # Substitute in the body, then wrap it in the safe binder
            pending.append(('lam', name))
            pending.append(('visit', body))

        else:
            raise TypeError(f'Unsupported target node: {type(current).__name__}')

    return values.pop()

def substitute(term: object, variable: str, replacement: object):
    """
    Return term with its free occurrences of variable replaced

    Inputs must be valid target ASTs with valid identifier strings
    Original nodes and the replacement must remain unchanged
    """

    # Reserve every original name, including unused binders, before choosing fresh names
    reserved = allNames(term) | allNames(replacement) | {variable}

    # Initialize one generator for the entire substitution
    fresh = FreshNames(reserved)

    # Compute replacement's free names once for all capture checks
    replacementFree = freeVariables(replacement)

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
