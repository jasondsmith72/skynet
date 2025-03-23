# Clarity Programming Language

Clarity is an AI-native programming language designed to make AI development more intuitive, efficient, and accessible. This implementation is part of the broader Skynet project, which aims to create a new computing paradigm centered around AI.

## Current Status

This is an early-stage implementation focused on establishing the foundational components of the Clarity language. The current implementation includes:

- **Lexer**: Tokenizes Clarity source code
- **Parser**: Converts tokens into an abstract syntax tree (AST)
- **Semantic Analyzer**: Checks for semantic errors
- **Example Programs**: Demonstrates syntax and features

## Language Features

Clarity is built around several core principles:

### AI-Native Design

- First-class support for tensors, models, and AI operations
- Built-in training and inference primitives
- Probabilistic programming constructs
- Gradient tracking

### MSP-Specific Capabilities

- Automated monitoring and remediation
- Intelligent resource management
- Context-aware alerting
- Multi-tenant optimization

### Safety and Reliability

- Rich type system with compile-time checks
- Self-healing code capabilities
- Runtime verification and adaptation
- Automatic error correction

## Folder Structure

- `compiler/`: Core compiler components
  - `lexer.py`: Tokenizes source code
  - `ast.py`: Abstract syntax tree nodes
  - `parser.py` & `parser_expressions.py`: Converts tokens to AST
  - `semantic_analyzer.py`: Checks for semantic errors
- `examples/`: Example Clarity programs
  - `image_classifier.clarity`: Simple CNN for image classification
  - `msp_monitoring.clarity`: Automated monitoring and remediation system
- `docs/`: Language documentation
- `runtime/`: Runtime support libraries
- `healing/`: Self-healing components
- `tests/`: Test suite
- `test_driver.py`: CLI for testing compiler components

## Getting Started

To test the language implementation:

```bash
# Process a Clarity source file
python -m clarity.test_driver -f path/to/example.clarity

# Test a code snippet
python -m clarity.test_driver -c "model Test { layers { } }"
```

## Example Code

```clarity
// Simple function example
func add(a: int, b: int) -> int {
    return a + b;
}

// AI model example
model SimpleClassifier {
    layers {
        conv1 = Conv2D(3, 32, kernelSize: 3, activation: relu);
        pool1 = MaxPool2D(2);
        flatten = Flatten();
        dense1 = Dense(32 * 13 * 13, 10, activation: softmax);
    }
    
    forward(input: tensor<float32[3, 28, 28]>) -> tensor<float32[10]> {
        var x = input;
        x = conv1(x);
        x = pool1(x);
        x = flatten(x);
        return dense1(x);
    }
}
```

## Next Steps

1. **Code Generation**: Adding backend code generation for target platforms
2. **Runtime Library**: Implementing core runtime support
3. **Optimization**: Performance optimizations for AI workloads
4. **Self-Healing**: Implementing self-healing capabilities
5. **Development Tools**: Building IDE integrations and tooling

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](../../docs/CONTRIBUTING.md) for details on how to get involved.

## License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.
