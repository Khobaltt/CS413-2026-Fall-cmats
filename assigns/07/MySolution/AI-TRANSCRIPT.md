# AI transcript

## Tools

I used OpenAI ChatGPT/Codex to help me create the implementation, tests, and documentation for this assignment. 
I gave the AI access to the assignment requirements, source code, and the code I wrote. 
No other person's code, accounts, or repository, was used.

## Important prompts

1. "Summarize the assignment. Draft a step-by-step checklist based on the assignment requirements. Give me a brief summary of the purpose of each step."
2. "What files will I need to implement to create the JSON-RPC service?"
3. "Write a draft for the file `<file_name>` and an explanation for what each class, method, etc. is meant to do. For each of these, also write a brief explanation for why it is correct."

## AI suggestions

- Separate the HTTP endpoint, JSON-RPC request handling, and LAMBDA3 operations into different files so each part has a clear responsibility.
- Use the provided LAMBDA3 parser, type-checker, interpreter, compilers, and formatters instead of duplicating their functionality.
- Run interpretation in a separate process so the service can stop computations that exceed the time limit.
- Distinguish malformed JSON, invalid requests, invalid parameters, language syntax errors, and type errors using the appropriate error codes.

## How generated output was reviewed and tested

I checked all code the AI wrote at each step and monitored the program behavior during testing. I reviewed all functions and tests and made changes when necessary. 