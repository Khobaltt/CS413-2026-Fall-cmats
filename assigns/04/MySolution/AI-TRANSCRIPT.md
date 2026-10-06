# AI assistance transcript and review record

## Tools

OpenAI ChatGPT/Codex was used to create the implementation, tests, and documentation. 
The AI was given access to the system requirements, python source code, and any code I wrote. 
No other person's code, accounts, private repository, or production service was used. The supplied interpreter was copied unchanged to `lambda1.py`.

## Important prompts

1. "Summarize the assignment. Create an implementation checklist from the assignment requirements. Identify the required functionality, placeholders, architectural boundaries, and documentation."
2. "Outline the MVC design for this LAMBDA front-end. What should the model, view, controller, and backend adapter each own? If any responsibilities overlap, propose a way to handle this."
3. "Write unit tests for the code input syntax, static analysis (free variables), execution, the model, controller, and HTTP interface." 
4. "Write drafts for any additional submission documents, including section headers and a few important bullet points to address."

## AI suggestions

- The AI proposed a restricted constructor AST reader, an HTTP-independent model, controller-coordinated backend calls, and separate browser rendering.
- The AI proposed spawned worker processes with a two-second timeout, explicit result outcomes, revision checks, and sentinel detection inside nested pairs.
- Implementation review identified that disabling the editor for each edit request could disrupt typing. Edit requests were serialized while retaining local editor text and allowing typing during draft synchronization; browser testing then exercised actual sequential keyboard input.
- The AI suggested Flask as the web framework with its role limited to HTTP routing, JSON adaptation, and serving static views. Official Flask documentation was consulted for routing and testing patterns.

## How the generated output was reviewed and tested

I reviewed all code the AI wrote and monitored the program behavior during testing. The AI also ran the automated suite with real supplied Lint and Interpret operations, including all expression forms, lexical scope, arithmetic, factorial/Fibonacci base cases, invalid constructor input, nested pair sentinels, and division by zero. Model-only tests enforce dirty/busy/revision rules; controller tests inject a fake backend to inspect dispatch, failures, and retries. A forced deadline exercises worker cleanup and retry.