# LAMBDA Testing Environment Requirements

## Purpose

## Stakeholders
Students will use this environment to write test programs in LAMBDA, a course-specific programming language. They will also be modifying and testing the LAMBDA compiler. Students should be able to do the following:

- Write, edit, and load LAMBDA programs from files
- Compile and run LAMBDA programs
- Parse compilation and execution errors
- Save programs to be accessed at a later time
- Maintain a collection of named tests
- Check whether compiler modifications break existing programs

Instructors will use this environment in lectures to demonstrate LAMBDA programs. They should be able to do the following:

- Quickly switch between examples
- Modify example programs without losing original copies
- Display program results clearly for students
- Inspect compiler information such as ASTs and generated code

## Scope
The app should be a browser-based LAMBDA programming and testing environment. It should be able to: 

- Be set up in a straightforward way in a browser students typically use
- View and edit LAMBDA source code
- Save and load programs to and from files
- Compile and run programs and display their results
- Display compilation errors and execution errors seperately
- Help users locate errors reported by the compiler
- Create named tests and collections of tests
- Test successful programs and programs expected to fail compilation
- Show a summary of test results
- Stop programs that run for too long
- Support sample compiler responses during development and demonstrations

### Outside of scope for first version
The first version of the app does not need to handle or include:

- Development of the LAMBDA compiler itself
- Public website access
- User accounts
- Simultaneous editing by multiple users
- Sophisticated visual effects

## Functional Requirements
FR-01: The system should provide a browser-based editor in which a user can enter, modify, and view LAMBDA source code.

Source: "I imagine opening the page, typing or pasting a short program, and asking the system to compile or run it."

Acceptance criteria:
- Starting conditions: The environment is open in a supported browser, and a new or existing LAMBDA program is open
- Action: The user enters LAMBDA source code into the editor, changes part of the code, and then views the editor contents
- Expected result: The editor displays the entered and modified source code accurately, without losing or unexpectedly changing the user's edits.

FR-02: The system should allow a user to load an existing LAMBDA program from a local file without manually re-entering its contents.

Source: "Students may already have programs saved in files, and they should not have to retype them."

Acceptance criteria:
- Starting conditions: A valid LAMBDA source file exists on the user's computer
- Action: The user selects the file using the environment's file-loading function
- Expected result: The contents of the selected file appear in the editor and are available for compilation or editing
- Failure scenario: The user selects a file that cannot be read or is not a valid supported LAMBDA source file
- Expected result: The system reports that the file could not be loaded and takes no further action

FR-03: The system should allow a user to save a LAMBDA program so that the user can return to it in a later session.

Source: "They should also be able to keep a program they have written and return to it later."

FR-04: The system should provide a set of example LAMBDA programs that a user can select and open for editing.

Source: "Having a few examples to start from would help."

FR-05: When a user opens an example for editing, the system should preserve access to the original example while allowing the user to modify a separate copy.

Source: "Students should be able to modify an example without losing access to the original."

FR-06: The system should allow a user to submit the current program to the LAMBDA compiler for compilation without executing the program.

Source: "Sometimes I only want to check whether a program compiles."

Acceptance criteria: 
- Starting conditions: The editor contains a syntactically correct LAMBDA program that produces a result if executed
- Action: The user selects the compile-only operation
- Expected result: The system sends the program to the compiler, reports whether compilation succeeded or failed, and does not execute the program

FR-07: The system should allow a user to submit the current program to the LAMBDA compiler for compilation and execution when execution is requested.

Source: "At other times, I want to run it and see the answer."

FR-08: The system should display the result of a successful program execution separately from compiler or system error messages.

Source: "A compilation error and a failure while running the program should not look like the same thing."

FR-09: If compilation fails, the system should display the compiler's error information and, when source-location information is provided, identify the corresponding location in the source program. 

Source: "When the compiler reports where the problem occurred, the environment should help the student find that place in the source."

Acceptance criteria:
- Starting conditions: The editor contains a LAMBDA program with a compilation error, for which the compiler will return a source location for that error
- Action: The user tries to compile the program
- Expected result: The system displays the compiler's error information and identifies or highlights the corresponding location in the source code. The error is clearly presented as a compilation error rather than an execution failure

FR-10: The system should distinguish compiler-connection or environment failures from errors in the user's LAMBDA program and should inform the user when the compiler cannot be reached.

Source: "The environment itself may have problems too. If it cannot reach the compiler, I do not want students to think their program is wrong."

FR-11: The system should allow a user to cancel an in-progress program execution. After cancellation, the system should indicate that the execution was stopped rather than presenting it as a normal program result.

Source: "There should be a way to stop it and move on."

Acceptance criteria:
- Starting conditions: A LAMBDA program is running and has not completed
- Action: The user selects the stop/cancel the running program
- Expected result: Program execution is terminated, the interface indicates that execution was stopped, and the system remains available for the user to edit or run another program

FR-12: The system should allow a user to create, name, edit, save, and delete individual tests containing a LAMBDA program and an expected outcome.

Source: "I would also like students to keep a collection of named tests."

FR-13: The system should support tests whose expected outcome is a successful result, such as an integer or Boolean value, and tests whose expected outcome is a compilation error.

Source: "Some tests would expect an answer, such as an integer or a Boolean value. Others would intentionally contain an error and expect the compiler to reject the program."

FR-15: When executing a test collection, the system should continue processing remaining tests if an individual test fails, is rejected by the compiler, or cannot be completed.

Source: "One troublesome test should not make the rest of the collection useless."

FR-16: After a test collection is executed, the system should provide a summary identifying which tests produced their expected outcomes and which did not, with enough information to investigate individual failures.

Source: "I would like a quick summary of which tests worked as expected, with enough detail to investigate the ones that did not."

Acceptance Criteria:
- Starting conditions: A test collection contains at least three tests: one expected to succeed, one expected to produce a compilation error, and one whose actual result differs from its expected result
- Action: The user runs the entire test collection
- Expected result: The system executes the tests and displays a summary showing which tests met their expected outcomes and which did not. The summary provides enough information to identify and investigate the failing test
- Failure scenario: One test cannot be completed because of an execution or compiler-connection failure
- Expected result: The system records that test as unsuccessful or incomplete with an appropriate explanation and continues processing the remaining tests rather than abandoning the entire collection

FR-17: The system should provide access to additional compiler-produced information, such as an abstract syntax tree or generated code, when that information is available through the compiler interface.

Source: "For teaching, it would also be useful to inspect information the compiler produces, such as an abstract syntax tree or generated code, when that information is available."

FR-18: The system should support a demonstration mode in which sample compiler responses can be displayed when the real compiler is unavailable, and those responses should be clearly identified as sample data rather than actual compilation results.

Source: "Using sample compiler responses for a demonstration would be acceptable at that stage, as long as nobody mistakes them for actual compilation results."

FR-19: The setup instructions should provide sufficient information for another person to install/start the first-version environment and connect the required compiler interface. The entire setup process should be documented

Source: "It should work in a browser students normally use, and the setup should be straightforward enough that another person can follow the instructions and get it running."

## Quality Requirements
QR-01: The system should remain usable for editing and navigation while compilation or execution is in progress; a long-running program should not prevent the user from interacting with the page.

QR-02: For ordinary actions such as editing text, selecting an example, opening a saved program, or switching between views, the system should provide visible feedback within 1 second under normal conditions. The 1-second target is a proposed acceptance target because the stakeholder did not specify a response time. (System response speed)

QR-03: Editing a program, compiling/running it, viewing results, and running tests should all be operable using a keyboard, and important status or error information should not be communicated through color alone. (Accessibility)

## Questions and Assumptions

### What is the exact notation that LAMBDA source code will use?
The source notation is still being discussed. However, the editor, file format, compiler interface, etc. will all depend on the source notation. (UNRESOLVED)

### How will the environment and the compiler communicate with each other?
The compiler is still under development, and the environment needs to know programs are submitted and how results and errors are returned. (UNRESOLVED) Assumptions:
- The environment will not provide the LAMBDA compiler itself
- The compiler will provide an interface the environment can communicate with

### What information needs to be stored when a program is saved?
The system needs to know whether it should only save source code or if should save other information such as compiler results, metadata, and test results. This will depend on what the client wants to do with saved files other than just loading programs. (UNRESOLVED)

### How long should the environment let a program run for before suggesting or forcing its termination?
The system needs a measurable limit to how the time long-running programs are allowed to run for. A short time limit may flag programs that are not actually stuck, and a long time limit could waste extra time. (UNRESOLVED) Assumptions:
- Set some measurable limit (time: 30 seconds; operations: N operations)

### What compiler information should be available to users and when?
The specifications say that ASTs and code generated by the compiler should be visible but only sometimes. The system needs to know what information to display at all times. (UNRESOLVED) Assumptions:
- Student view: limited information available
- Instructor (advanced) view: ASTs and compiler-generated code available
- There exists some way to switch between views

### Should programs remain available after closing and reopening the browser?
The specifications say that students should be able to return to their work in another session. The storage and user identification requirements depend on how programs in the environment need to be saved. (UNRESOLVED) Assumptions:
- User accounts are not required
- Saved work will persist between sessions (storage method is currently unresolved)