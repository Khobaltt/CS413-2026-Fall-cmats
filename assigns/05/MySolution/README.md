## System requirements

`python3 --version` must show version 3.12 or later. 

## Setup and independent test commands

Run all commands from the directory `CS413-2026-Fall-cmats/assigns/05`, where `lambda1_vp.py` lives.

```sh
# create an isolated environment and install the only testing dependency
python3 -m venv .venv
.venv/bin/python -m pip install pytest

# run only the standard-library TestCase suite
.venv/bin/python -m unittest discover -s MySolution -p 'test_unittest.py' -v

# run only the pytest-function suite, independently of the unittest suite
.venv/bin/python -m pytest MySolution/test_pytest.py -q
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

Before substitution, `AllNamesVisitor` collects every variable occurrence and
binder declaration in both original trees and reserves the target.
A conflicting binder named `y` tries `y_1`, `y_2`, etc., skipping every
already-reserved name. Each generated name is immediately reserved for the entire call.
Counters are per original binder name and restart for each public entry-point
call. Children are visited left to right: a let initializer is visited before
its body, fix function names are processed before parameters. Equal fix binder
names share one fresh name. Binders are renamed when the target is free in
their body and the target is not bound by that binder.

## limitations

The operations assume valid supplied ASTs and identifiers, as defined by the
assignment. Since traversal is recursive, extremely deep trees may exceed Python's
recursion limit. Repeated free-variable checks can take quadratic time on deep
binder chains. 