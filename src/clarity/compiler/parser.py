"""
Clarity Programming Language Parser

This module implements the parser for the Clarity programming language, which 
converts a stream of tokens into an abstract syntax tree (AST).
"""

from typing import List, Optional, Dict, Set, Tuple, Any
from .lexer import Token, TokenType, tokenize
from .ast import *


class ParseError(Exception):
    """Exception raised for parsing errors."""
    
    def __init__(self, token: Token, message: str):
        self.token = token
        self.message = message
        super().__init__(f"Parse error at line {token.line}, column {token.column}: {message}")


class Parser:
    """
    Parser for the Clarity programming language.
    
    This class converts a sequence of tokens from the lexer into an AST.
    """
    
    def __init__(self, tokens: List[Token]):
        """
        Initialize the parser with a list of tokens.
        
        Args:
            tokens: List of tokens from the lexer
        """
        self.tokens = tokens
        self.current = 0
    
    def parse(self) -> Program:
        """Parse tokens into a Program AST node."""
        program = Program()
        
        # Parse imports, functions, and models until end of file
        while not self.is_at_end():
            try:
                decorators = []
                while self.check(TokenType.DECORATOR):
                    decorators.append(self.advance().value)

                if self.match(TokenType.IMPORT):
                    if decorators:
                        self.error(self.previous(), "Decorators are not allowed on import statements.")
                    program.imports.append(self.parse_import())
                elif self.match(TokenType.FUNC):
                    program.functions.append(self.parse_function(decorators))
                elif self.match(TokenType.MODEL):
                    program.models.append(self.parse_model(decorators))
                else:
                    # Skip unexpected tokens and try to recover
                    if decorators:
                        self.error(self.peek(), "Decorators can only be applied to functions or models.")
                    elif not self.is_at_end():
                        self.error(self.peek(), "Expected import, func, or model declaration")
                        self.advance()
            except ParseError as e:
                # Report the error and try to synchronize
                print(e)
                self.synchronize()
        
        return program
    
    # Helper methods for token handling
    def is_at_end(self) -> bool:
        """Check if we've reached the end of the token stream."""
        return self.peek().type == TokenType.EOF
    
    def peek(self) -> Token:
        """Return the current token without consuming it."""
        return self.tokens[self.current]
    
    def previous(self) -> Token:
        """Return the most recently consumed token."""
        return self.tokens[self.current - 1]
    
    def advance(self) -> Token:
        """Consume the current token and return it."""
        if not self.is_at_end():
            self.current += 1
        return self.previous()
    
    def check(self, type: TokenType) -> bool:
        """Check if the current token is of the given type."""
        if self.is_at_end():
            return False
        return self.peek().type == type
    
    def match(self, *types: TokenType) -> bool:
        """Check if the current token matches any of the given types."""
        for type in types:
            if self.check(type):
                self.advance()
                return True
        return False
    
    def consume(self, type: TokenType, message: str) -> Token:
        """Consume the current token if it matches the expected type."""
        if self.check(type):
            return self.advance()
        raise self.error(self.peek(), message)
    
    def error(self, token: Token, message: str) -> ParseError:
        """Create a parse error at the given token."""
        return ParseError(token, message)
    
    def synchronize(self) -> None:
        """Skip tokens until a statement boundary is found."""
        self.advance()
        
        while not self.is_at_end():
            if self.previous().type == TokenType.SEMICOLON:
                return
            
            if self.peek().type in {
                TokenType.FUNC,
                TokenType.VAR,
                TokenType.MODEL,
                TokenType.IF,
                TokenType.FOR,
                TokenType.WHILE,
                TokenType.RETURN,
                TokenType.IMPORT
            }:
                return
            
            self.advance()
    
    # The rest of the parser implementation follows...
    # We'll implement these in a separate file to keep this one shorter

# Convenience function to parse source code
def parse(source: str) -> Program:
    """
    Parse Clarity source code into an AST.
    
    Args:
        source: Clarity source code as a string
        
    Returns:
        Program AST node representing the parsed code
    """
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse()
