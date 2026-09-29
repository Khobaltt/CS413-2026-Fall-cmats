# LAMBDA Testing Environment Requirements

## Stakeholders and Scope

### Primary users:
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

### Within scope
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

## Questions and Assumptions

## Requirements Specification

## Acceptance Criteria

## Tracability and Review