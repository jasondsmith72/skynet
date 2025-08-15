"""
Clarity Programming Language Test Driver

This script provides a simple CLI for testing the Clarity compiler components.
It allows lexing, parsing, and semantic analysis of Clarity source files or 
inline code snippets.
"""

import argparse
import sys
import os
from typing import List, Optional, Dict, Any

from .compiler.lexer import tokenize, Token, TokenType
from .compiler.parser import parse
from .compiler.semantic_analyzer import SemanticAnalyzer, SemanticError


def print_tokens(tokens: List[Token]) -> None:
    """Print tokens in a readable format."""
    for token in tokens:
        print(f"{token.line:4d}:{token.column:2d} {token.type.name:15s} {token.value}")


def test_lexer(source: str) -> List[Token]:
    """
    Test the lexer on a source string.
    
    Args:
        source: Clarity source code
        
    Returns:
        List of tokens from the lexer
    """
    print("=== LEXER TEST ===")
    try:
        tokens = tokenize(source)
        print_tokens(tokens)
        return tokens
    except Exception as e:
        print(f"Error during lexing: {e}")
        return []


def test_parser(source: str) -> Optional[Any]:
    """
    Test the parser on a source string.
    
    Args:
        source: Clarity source code
        
    Returns:
        The AST if parsing succeeds, None otherwise
    """
    print("\n=== PARSER TEST ===")
    try:
        ast = parse(source)
        print("Parsing successful!")
        print(f"AST structure: {type(ast).__name__}")
        print(f"- {len(ast.imports)} imports")
        print(f"- {len(ast.functions)} functions")
        print(f"- {len(ast.models)} models")
        return ast
    except Exception as e:
        print(f"Error during parsing: {e}")
        return None


def test_semantic_analyzer(ast: Any) -> List[SemanticError]:
    """
    Test the semantic analyzer on an AST.
    
    Args:
        ast: The AST to analyze
        
    Returns:
        List of semantic errors
    """
    print("\n=== SEMANTIC ANALYZER TEST ===")
    if ast is None:
        print("No AST to analyze")
        return []
    
    try:
        analyzer = SemanticAnalyzer()
        errors = analyzer.analyze(ast)
        
        if errors:
            print(f"Found {len(errors)} semantic errors:")
            for i, error in enumerate(errors, 1):
                print(f"{i}. Line {error.line}, Column {error.column}: {error.message}")
        else:
            print("No semantic errors found!")
        
        return errors
    except Exception as e:
        print(f"Error during semantic analysis: {e}")
        return []


def process_file(filename: str) -> None:
    """
    Process a Clarity source file through the compiler pipeline.
    
    Args:
        filename: Path to the Clarity source file
    """
    try:
        with open(filename, 'r') as f:
            source = f.read()
        
        print(f"Processing file: {filename}")
        tokens = test_lexer(source)
        ast = test_parser(source)
        errors = test_semantic_analyzer(ast)
        
        if not errors:
            print("\nCompilation successful!")
        else:
            print(f"\nCompilation failed with {len(errors)} errors.")
    
    except FileNotFoundError:
        print(f"Error: File not found: {filename}")
    except Exception as e:
        print(f"Error processing file: {e}")


def process_snippet(snippet: str) -> None:
    """
    Process a Clarity code snippet through the compiler pipeline.
    
    Args:
        snippet: Clarity source code snippet
    """
    print("Processing code snippet:")
    print("---")
    print(snippet)
    print("---")
    
    tokens = test_lexer(snippet)
    ast = test_parser(snippet)
    errors = test_semantic_analyzer(ast)
    
    if not errors:
        print("\nCompilation successful!")
    else:
        print(f"\nCompilation failed with {len(errors)} errors.")


def main() -> None:
    """Main entry point for the test driver."""
    parser = argparse.ArgumentParser(description="Clarity Language Test Driver")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help="Process a Clarity source file")
    group.add_argument('-c', '--code', help="Process a Clarity code snippet")
    
    parser.add_argument('-o', '--output', help="Output file for results (default: stdout)")
    
    args = parser.parse_args()
    
    # Redirect output if requested
    if args.output:
        sys.stdout = open(args.output, 'w')
    
    try:
        if args.file:
            process_file(args.file)
        elif args.code:
            process_snippet(args.code)
    
    finally:
        # Restore stdout if needed
        if args.output:
            sys.stdout.close()
            sys.stdout = sys.__stdout__


if __name__ == "__main__":
    main()
