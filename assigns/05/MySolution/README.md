## System requirements

`python3 --version` must show version 3.12 or later. 

## Setup and independent test commands

Run all commands from `CS413-2026-Fall-cmats`, the assignment directory.

```sh
# create an isolated environment and install the only testing dependency
python3 -m venv .venv
.venv/bin/python -m pip install pytest

# run only the standard-library TestCase suite
PYTHONPATH=assigns/05 python3 -m unittest discover -s assigns/05/MySolution -p 'test_unittest.py' -v

# run only the pytest-function suite, independently of the unittest suite
PYTHONPATH=assigns/05 python3 -m pytest assigns/05/MySolution/test_pytest.py -q
```

## Example

```python
# build syntax with the existing expression classes, then use the new visitors.
from lambda1_vp import D0Eapp, D0Elam, D0Eop2, D0Evar, D0Eint
from MySolution import d0exp_pretty, d0exp_substitute

expression = D0Eapp(
    D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1))), D0Eint(4)
)
print(d0exp_pretty(expression))  # ((lam x. (x + 1)) 4)

# free replacement y stays free because the original binder is renamed
expression = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
result = d0exp_substitute(expression, "x", D0Evar("y"))
print(d0exp_pretty(result))  # (lam y_1. (y + y_1))
```

## fresh-name policy

Before substitution, `AllNamesVisitor` collects every variable occurrence and binder declaration in both original trees and reserves the target.
A conflicting binder named `y` tries `y_1`, `y_2`, etc., skipping every already-reserved name. 
Each generated name is immediately reserved for the entire call.
Counters are per original binder name and restart for each public entry-point call. 
Children are visited left to right: a let initializer is visited before its body, fix function names are processed before parameters. 
Equal fix binder names share one fresh name. 
Binders are renamed when the target is free in their body and the target is not bound by that binder.

## limitations

The operations assume valid supplied ASTs and identifiers, as defined by the assignment. 
Since traversal is recursive, extremely deep trees may exceed Python's recursion limit. 
Repeated free-variable checks can take quadratic time on deep binder chains. 

## Design explanation

The supplied visitor interface separates expression structure from operations.
Each expression's `accept` method calls the visitor method for its constructor.
`PrettyPrintVisitor` gives a result type of `str`. 
It combines child strings with the exact spaces and parentheses required by the assignment.
`SubstitutionVisitor` gives a result type of `d0exp`, producing another syntax tree. 
`AllNamesVisitor` returns sets of strings. 
The supplied free-variable visitor returns a frozen set. 
These different result types use the same expression classes and dispatch mechanism.

Substitution carries context in the target name, replacement expression, and a fresh-name generator shared across the traversal. 
It also records the replacement's free names, which identify possible capture. 
At a variable, it returns the replacement object when the name matches and otherwise keeps the original variable. 
It never visits an inserted replacement, so a replacement containing the target does not trigger further substitution.
Regular constructors rebuild their children through `accept`. 
Unchanged literal leaves and blocked bodies can be reused because no method assigns to an input expression's fields.

Binding constructors require separate scope decisions. 
A lambda binds its parameter in its body. 
A fix binds both names in its body. 
A let binds its name only in its body, so its initializer is always visited seperately. 
If a binder binds the target, substitution stops in that body. 
If the target is not free there, the body does not need renaming. 
Otherwise, every binder conflicting with a free replacement name receives a fresh name before insertion.

`RenameVisitor` changes occurrences connected to the enclosing renamed binder.
Its mapping is narrowed when a nested lambda, fix, or let introduces a matching name, preserving shadowing. 
A nested let's initializer uses the original mapping because its declaration does not bind there. 
Equal fix binder names are renamed together to one name, retaining the parameter's precedence over the function binding. 
The all-name reservation prevents new names from interfering with any nested declarations or replacement names.

Adding an operation means adding a visitor with methods for the existing constructors. 
Therefore, the AST classes need no changes. 
Adding an expression constructor requires a class and dispatch method, extending the visitor interface, and updating every operation to handle the new form. 
This design therefore makes new operations straightforward while requiring coordinated work for new syntax. 
Tests independently check exact output and scope properties without using evaluation to judge the transformations.