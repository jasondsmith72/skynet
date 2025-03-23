# Clarity Language Test Suite

## Overview

This directory contains comprehensive tests for the Clarity programming language. The tests cover syntax parsing, semantic analysis, and code generation to ensure the language implementation is correct and robust.

## Test Categories

### Syntax Tests

`test_syntax.py` contains tests for the language syntax parser. It verifies that valid Clarity code is correctly parsed into the appropriate AST structure and that invalid code is properly rejected with meaningful error messages.

Syntax tests cover:

- Basic language constructs (variables, functions, classes, etc.)
- Control flow (if, for, while, switch, etc.)
- Error handling (try-catch)
- AI integration features
- Agent and service declarations
- Type definitions

### Semantic Tests

`test_semantics.py` (to be implemented) will test the semantic analysis phase, which checks that code is not just syntactically valid but also makes sense according to Clarity's type system and rules.

Semantic tests will cover:

- Type checking
- Identifier scope and resolution
- Agent permission validation
- Intent verification
- Error handling validation

### Code Generation Tests

`test_codegen.py` (to be implemented) will test the code generation phase, which transforms Clarity code into executable code or intermediate representation.

Code generation tests will cover:

- Function compilation
- Class and type compilation
- AI integration compilation
- Agent and service compilation
- Self-healing mechanism compilation

## Running the Tests

To run all tests:

```bash
python -m unittest discover -s src/clarity/tests
```

To run a specific test file:

```bash
python -m unittest src/clarity/tests/test_syntax.py
```

To run a specific test case:

```bash
python -m unittest src.clarity.tests.test_syntax.TestClarity.test_hello_world
```

## Adding New Tests

When adding new features to the Clarity language, you should also add corresponding tests. Follow these guidelines:

1. Place syntax tests in `test_syntax.py`
2. Place semantic tests in `test_semantics.py`
3. Place code generation tests in `test_codegen.py`
4. Use descriptive test method names that indicate what's being tested
5. Include both positive tests (valid code) and negative tests (invalid code)
6. For negative tests, check that the correct error is raised

## Test Data

Sample Clarity code for testing can be found in the `examples` directory. These examples serve both as documentation of language features and as test inputs.

When adding new language features, consider adding example code that demonstrates the feature to the examples directory.

## Continuous Integration

These tests are run automatically as part of the CI/CD pipeline. All tests must pass before code can be merged into the main branch.

## Code Coverage

We aim for high code coverage in our tests. Run the coverage tool to check test coverage:

```bash
python -m coverage run -m unittest discover -s src/clarity/tests
python -m coverage report
```