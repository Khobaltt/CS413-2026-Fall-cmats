# AI transcript

## Tools

OpenAI ChatGPT/Codex was used to create the implementation, tests, and documentation. 
The AI was given access to my program requirements, source code, and the code I wrote. 
No other person's code, accounts, or repository, was used.

## Important prompts

1. "Summarize the assignment. Using the requirements, create a step-by-step checklist. Additionally, make a checklist of all project requirements. Then, make a list of files I will need to include in my submission and explain the functionality of each one."
2. "Write an outline for `<file_name>` (for example, all classes and methods required) and include TODO: blocks for me to fill out."
3. "Verify that `<method_name>` functions correctly. Give me a few test cases and their expected output."

## AI suggestions

- Suspend the initial search and each event’s remaining computation in lazy stream cells. This allows the client to stop after any event without evaluating the rest of the search.
- Separate the LAMBDA3 solver, stream management, JSON-RPC dispatcher, and browser rendering into different modules so each part can be reviewed and tested independently.
- Represent each event with a board snapshot and relevant coordinates. This makes placements, rejections, and backtracking easier to display and verify.
- Test laziness using observable evaluation counters and a deliberately failing delayed computation, rather than relying only on a value being displayed as lazy.

## How generated output was reviewed and tested

Most of the assignment was outlined or written by AI but verified by me. I checked that each class, method, function, etc. that the AI suggested made sense and worked with each other. 

Much of the test scripts were written by AI. I checked whatever code the AI wrote myself and wrote smaller tests by hand to verify its work. I also had AI write tests for its own code, which I looked over as well. 