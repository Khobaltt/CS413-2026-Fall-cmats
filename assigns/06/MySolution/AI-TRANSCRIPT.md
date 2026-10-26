# AI transcript

## Tools

I used OpenAI ChatGPT/Codex to create the implementation, tests, and documentation. 
I gave the AI access to my program requirements, source code, and the code I wrote. 
No other person's code, accounts, or repository, was used.

## Important prompts

1. "Summarize the assignment. Break it down into a step-by-step checklist. Additionally, make a checklist of all project requirements. Then, make a list of files I will need to include in my submission, documenting the functionality of each one."
2. "Write an outline for `<file_name>` (for example, all classes and methods required) and include TODO: blocks for me to fill out."
3. "Verify that `<method_name>` functions correctly. Give me a few test cases and their expected output."

## AI suggestions

- Use delayed branches for conditionals and short-circuit operators. The AI suggested wrapping branches in lambda expressions so call-by-value evaluation would evaluate only the selected branch.
- Implement recursion using the Z combinator. The AI recommended Z because it delays recursive self-application appropriately for call-by-value evaluation.
- Test budget boundaries explicitly. The AI suggested checking that a lambda completes with zero steps and that an expression finishing on its final permitted step reports success.
- Separate execution from observation. The AI recommended separate budgets and step counts for evaluating compiled terms and decoding Church-encoded results.

## How generated output was reviewed and tested

Most of the assignment was outlined by AI but written by me. I checked that each class, method, function, etc. that the AI suggested made sense and worked with each other. 

Much of the test scripts were written by AI. I checked whatever code the AI wrote myself and wrote smaller tests by hand to verify its work. I also had AI write tests for its own code, which I looked over as well. 