# Clarity Self-Healing System Guide

This guide explains how to use and test the self-healing capabilities of the Clarity programming language.

## Overview

Clarity's self-healing system automatically detects, diagnoses, and fixes errors in your code. Key components include:

1. **Diagnostic Runtime**: Monitors code execution and captures error context
2. **Error Analyzer**: Identifies error patterns and root causes
3. **Healing Engine**: Applies appropriate fixes for different error types

## How It Works

### 1. Error Detection

When an error occurs during code execution, the diagnostic runtime captures:

- Error message and stack trace
- Execution context (variables, scope, etc.)
- Recent execution history
- Code surrounding the error location

### 2. Error Analysis

The error analyzer examines the captured information to:

- Classify the error type (syntax, reference, type, logic)
- Identify specific error patterns
- Determine the root cause
- Evaluate the context for potential fixes

### 3. Self-Healing

The healing engine then:

- Selects appropriate healing strategies based on the error type
- Applies fixes to the code
- Validates the fixed code through virtual execution
- Learns from successful and unsuccessful healing attempts

## Supported Error Types

Clarity's self-healing system can currently detect and fix the following types of errors:

### Syntax Errors
- **Missing Semicolons**: Automatically adds missing semicolons at the end of statements
- **Missing Braces**: (Coming soon) Will detect and add missing braces in control structures

### Reference Errors
- **Undefined Variables**: Automatically declares undefined variables with appropriate initial values
- **Undefined Functions**: (Coming soon) Will create stub implementations for undefined functions

### Type Errors
- **String-Number Conversion**: Automatically adds parseFloat() to convert strings to numbers in arithmetic operations
- **String Literal to Number**: Converts string literals containing numeric values to actual numbers
- **Type Mismatches**: Identifies type compatibility issues and adds appropriate conversions

### Logic Errors
- **Infinite Loops**: (Coming soon) Will detect and fix potential infinite loops
- **Off-by-One Errors**: (Coming soon) Will identify and correct array index issues and loop boundaries

## Using Self-Healing in Your Code

### Intent Declarations

Clarity allows you to declare the intent of functions, which helps the self-healing system understand what your code is supposed to do:

```clarity
intent "Calculate the average of a list of numbers"
function average(numbers) {
    let sum = 0;
    for (let i = 0; i < numbers.length; i++) {
        sum += numbers[i];
    }
    return sum / numbers.length;
}
```

If the function has a bug or doesn't fulfill its declared intent, the self-healing system can detect and fix it.

### Explicit Healing Requests

You can also explicitly request healing for a code block:

```clarity
heal {
    // Potentially problematic code
    let result = complexCalculation();
    processResult(result);
}
```

The runtime will monitor this block more closely and attempt to heal any issues that arise.

### Learning From Your Code

The self-healing system improves over time by learning from your code patterns. You can help it learn by marking correct code:

```clarity
learn {
    // Example of correct implementation
    function correctImplementation() {
        // ...
    }
}
```

## Type Conversion Examples

### String-to-Number Conversion

Clarity will automatically detect and fix type mismatches involving strings and numbers:

```clarity
// Original code with error
let price = "10";
let quantity = 5;
let total = price * quantity;  // TypeError: Cannot multiply string and number

// Automatically healed by Clarity
let price = "10";
let quantity = 5;
let total = parseFloat(price) * quantity;  // Adds parseFloat() to convert string to number
```

### String Literal Conversion

When a string literal contains a number that should be used in calculations:

```clarity
// Original code with error
let price = "10";  // String that should be a number
let quantity = 5;
let total = price * quantity;  // TypeError: Cannot multiply string and number

// Automatically healed by Clarity (alternative approach)
let price = 10;  // Converted to numeric literal
let quantity = 5;
let total = price * quantity;  // Now works correctly
```

## Testing Self-Healing

### Creating Test Cases

You can create test cases with intentional errors to verify the self-healing capabilities:

1. Create a file with known errors (see `examples/error_example.clarity`)
2. Run it through the diagnostic runtime
3. Verify the healing results

### Using the Test Suite

The test suite in `tests/test_self_healing.py` demonstrates how to programmatically test healing:

```bash
# Run all self-healing tests
python -m src.clarity.tests.test_self_healing

# Run a specific test
python -m src.clarity.tests.test_self_healing TestSelfHealing.test_missing_semicolon_healing
```

### Analyzing Healing Performance

The healing engine tracks success rates for different error types. You can access these statistics:

```python
from clarity.healing.healing_engine import HealingEngine

engine = HealingEngine()
# ... after running some tests
print(engine.healing_success_rate)
```

## Extending the Self-Healing System

### Adding New Error Patterns

To add support for a new error pattern:

1. Add the pattern to `ErrorAnalyzer.load_patterns()`
2. Implement a context analyzer if needed
3. Create a healing strategy in `HealingEngine`
4. Add the strategy to the appropriate category in `load_healing_strategies()`

### Creating Custom Healing Strategies

Custom healing strategies are functions that follow this pattern:

```python
def heal_custom_error(self, code, analysis, context=None):
    """Heal a custom error type."""
    # Analyze the error and code
    # Apply transformations to fix the error
    healed_code = transform(code)
    
    return {
        "success": True,
        "message": "Fixed the custom error",
        "original_code": code,
        "healed_code": healed_code,
        "confidence": 0.8
    }
```

## Next Steps

- Implement more healing strategies for common error patterns
- Enhance the learning system to improve over time
- Add support for more complex code analysis
- Integrate with development tools and environments

By using the self-healing capabilities of Clarity, you can spend less time debugging and more time solving real problems.