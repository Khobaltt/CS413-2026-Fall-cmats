# AI transcript

## Tools

I used OpenAI ChatGPT/Codex to create the implementation, tests, and documentation. 
I gave the AI access to my program requirements, source code, and the code I wrote. 
No other person's code, accounts, or repository, was used.

## Important prompts

1. "Summarize the assignment. Draft a step-by-step checklist based on the assignment requirements. Give me a brief summary of the purpose of each step."
2. "What files will I need to implement to add the pretty printing and substitution operations to the LAMBDA AST?"
3. "Write an outline for `<file_name>` (for example, all classes and methods required)."

## AI suggestions

- The AI helped me to outline the general approach for this assignment: Use `accept` for every expression traversal. Give each constructor a visitor method and recursively visit its children through `accept`. Apply this to helper visitors as well.
- The AI helped me to plan my fresh-name policy: Collect all names before generating fresh names. Reserve variable occurrences, binder declarations, the target, and names generated earlier in the call. Collecting only free variables can miss collisions with nested binders.
- The AI suggested the `examples.py` helper file to assist seperate testing suites: `test_pytest.py` and `test_unittest.py`. 

## How generated output was reviewed and tested

I checked all code the AI wrote at each step and monitored the program behavior during testing. I reviewed all functions and tests and made changes when necessary. 