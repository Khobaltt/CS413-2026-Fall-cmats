## 1. lambda1_vp.py

Introduce the two operations: computing free variables and evaluating an expression. Students should know Python classes and basic lambda calculus. The interpreter builds syntax directly with constructors rather than parsing source text.

## 2. The interpreter at a glance

Source: lambda1_vp.py, D0E000, D0V000, ENV000 and the two public wrapper functions. Explain that the same expression supports multiple operations via accept.

## 3. Expression constructors

Source: expression dataclasses. arg1, arg2 and arg3 are positional fields whose meaning depends on the constructor. D0Elam stores parameter and body. D0Efix stores function name, parameter and body. ctag labels remain but accept controls dispatch.

## 4. Each node chooses a visitor method

Source: D0Eint.accept. Snippet omits @dataclass and ctag for space. Trace D0Eint(7).accept(EvaluateVisitor()): the expression calls visit_int on that particular visitor and gets D0Vint(7). A FreeVariableVisitor instead returns frozenset().

## 5. Python 3.12 type parameters

Source: D0ExpVisitor and expression accept methods. The class R and the method R have distinct scopes. D0ExpVisitor[R] in accept relates the supplied visitor result to the method return type. Existing type alias statements also use Python 3.12 syntax. Abstract methods require concrete visitors to implement every expression case.

## 6. Free variables follow lexical binding

Source: FreeVariableVisitor. Mathematical pseudocode uses | for set union, matching Python set notation. For op2, application and pair, take the union of child sets. For if0, include all three children even though evaluation chooses just one branch. Free-variable analysis does not execute expressions.

## 7. A let binder covers only its body

Source: FreeVariableVisitor.visit_let. Ask why the x in the initializer survives. Let is nonrecursive: the new x is unavailable until the initializer has completed. The printed order of a frozenset is unspecified.

## 8. Environments store bindings

Source: ENVnil, ENVcns and d0env_search. Frozen dataclasses prevent rebinding environment fields, but stored values are not deeply immutable. Missing names return D0V000(), an error sentinel rather than a NameError. New scopes use a new EvaluateVisitor so the caller environment stays intact.

## 9. Values and closures

Source: runtime value dataclasses, EvaluateVisitor.visit_lam and visit_fix. Snippets omit type annotations. A closure packages code together with the lexical context needed when it runs later. The implementation captures the whole environment, without using the free-variable visitor to trim it.

## 10. Function application evaluates both sides

Source: EvaluateVisitor.visit_app, lambda branch. Argument evaluation uses the calling visitor. Body evaluation uses the closure environment extended with its parameter. Even an unused argument evaluates first. An invalid function value triggers TypeError after both expressions have been evaluated.

## 11. Lexical scoping preserves the original x

Source: EvaluateVisitor.visit_let, visit_lam and visit_app. This is surface pseudocode for a nested constructor expression. Ask students to predict 11 versus 101 before revealing the trace. The caller has x=100, but application extends the defining environment where x=10.

## 12. Recursive closures bind their own name

Source: EvaluateVisitor.visit_app, fix branch. dfix.arg1 is the recursive name, arg2 is the parameter and arg3 is the body. Bind the function name to the same closure, then bind the parameter. Each recursive call builds a fresh scope. No cyclic environment is needed at closure creation. If the parameter and recursive name coincide, the parameter is the newest binding and shadows the recursive name.

## 13. Conditionals, pairs and operators

Source: EvaluateVisitor.visit_if0, visit_pair, visit_pfst, visit_psnd, visit_op1 and visit_op2. Comments show evaluation results, not the immediate constructor result. Unary operators are +1 and -1. Binary operators are +, -, *, /, <, >, <=, >=, ==, !=. Division uses Python // and therefore floors negative quotients. Division by zero propagates ZeroDivisionError.

## 14. One syntax, two operations

Source: wrapper functions, FreeVariableVisitor.visit_if0 and EvaluateVisitor.visit_if0. This example emphasizes the difference between syntactic dependency analysis and a particular execution. Analysis sees the name in the unselected branch. Evaluation never looks it up.

## 15. Extending the visitor design

Source: D0ExpVisitor abstract interface and concrete visitors. Discuss the visitor tradeoff: adding operations is localized, while adding variants affects every visitor. A static type checker would need its own language type representation and binding environment. D0E000.accept rejects unsupported expression instances. This interpreter does not provide a parser or a static type checker.

## 16. Questions for discussion

Answers: 1. {y}. 2. Argument evaluation raises ZeroDivisionError before entering the body. 3. f captures x=10 and later binds y=1 in that environment. 4. Add D0Eneg.accept, add abstract visit_neg to D0ExpVisitor and implement it in FreeVariableVisitor and EvaluateVisitor. Source: lambda1_vp.py. Suggested live demo: run python3.12 -m unittest discover -s TEST -p "test_*.py".
