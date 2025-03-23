#!/usr/bin/env python3
"""
Lexer for the Clarity programming language.

This module provides the lexical analyzer (lexer) for Clarity, which converts
source code text into a stream of tokens that can be processed by the parser.
"""

import re
from enum import Enum, auto
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass

class TokenType(Enum):
    """Enumeration of token types in the Clarity language."""
    # Literals
    INTEGER = auto()    # 42
    FLOAT = auto()      # 3.14
    STRING = auto()     # "hello"
    BOOLEAN = auto()    # true, false
    NULL = auto()       # null
    
    # Identifiers and Keywords
    IDENTIFIER = auto() # variable names, function names, etc.
    KEYWORD = auto()    # language keywords
    
    # Operators
    PLUS = auto()       # +
    MINUS = auto()      # -
    MULTIPLY = auto()   # *
    DIVIDE = auto()     # /
    MODULO = auto()     # %
    
    EQUAL = auto()      # ==
    NOT_EQUAL = auto()  # !=
    GREATER = auto()    # >
    GREATER_EQUAL = auto() # >=
    LESS = auto()       # <
    LESS_EQUAL = auto() # <=
    
    AND = auto()        # &&
    OR = auto()         # ||
    NOT = auto()        # !
    
    ASSIGN = auto()     # =
    PLUS_ASSIGN = auto() # +=
    MINUS_ASSIGN = auto() # -=
    MULTIPLY_ASSIGN = auto() # *=
    DIVIDE_ASSIGN = auto() # /=
    MODULO_ASSIGN = auto() # %=
    
    # Delimiters
    LEFT_PAREN = auto() # (
    RIGHT_PAREN = auto() # )
    LEFT_BRACE = auto() # {
    RIGHT_BRACE = auto() # }
    LEFT_BRACKET = auto() # [
    RIGHT_BRACKET = auto() # ]
    
    COMMA = auto()      # ,
    DOT = auto()        # .
    SEMICOLON = auto()  # ;
    COLON = auto()      # :
    QUESTION = auto()   # ?
    ARROW = auto()      # ->
    DOT_DOT = auto()    # ..
    
    # Special
    TEMPLATE_STRING = auto() # String with embedded expressions: "Value: ${expr}"
    COMMENT = auto()    # // Single line comment or /* Multi-line comment */
    WHITESPACE = auto() # Spaces, tabs, newlines
    EOF = auto()        # End of file marker
    ERROR = auto()      # Invalid token

@dataclass
class Token:
    """Represents a token in the Clarity language."""
    type: TokenType
    lexeme: str
    value: Any = None
    line: int = 0
    column: int = 0
    
    def __str__(self) -> str:
        return f"{self.type.name}({repr(self.lexeme)})"

class Lexer:
    """Lexical analyzer for the Clarity language."""
    
    def __init__(self):
        """Initialize the lexer."""
        # Keywords in the Clarity language
        self.keywords = {
            "function": TokenType.KEYWORD,
            "class": TokenType.KEYWORD,
            "interface": TokenType.KEYWORD,
            "type": TokenType.KEYWORD,
            "enum": TokenType.KEYWORD,
            "let": TokenType.KEYWORD,
            "const": TokenType.KEYWORD,
            "if": TokenType.KEYWORD,
            "else": TokenType.KEYWORD,
            "for": TokenType.KEYWORD,
            "while": TokenType.KEYWORD,
            "switch": TokenType.KEYWORD,
            "case": TokenType.KEYWORD,
            "default": TokenType.KEYWORD,
            "return": TokenType.KEYWORD,
            "throw": TokenType.KEYWORD,
            "try": TokenType.KEYWORD,
            "catch": TokenType.KEYWORD,
            "finally": TokenType.KEYWORD,
            "in": TokenType.KEYWORD,
            "guard": TokenType.KEYWORD,
            "using": TokenType.KEYWORD,
            "ai": TokenType.KEYWORD,
            "agent": TokenType.KEYWORD,
            "service": TokenType.KEYWORD,
            "permissions": TokenType.KEYWORD,
            "capabilities": TokenType.KEYWORD,
            "constraints": TokenType.KEYWORD,
            "config": TokenType.KEYWORD,
            "schedule": TokenType.KEYWORD,
            "on": TokenType.KEYWORD,
            "event": TokenType.KEYWORD,
            "intent": TokenType.KEYWORD,
            "recoveryStrategies": TokenType.KEYWORD,
            "this": TokenType.KEYWORD,
            "super": TokenType.KEYWORD,
            "extends": TokenType.KEYWORD,
            "implements": TokenType.KEYWORD,
            "async": TokenType.KEYWORD,
            "await": TokenType.KEYWORD,
            "throws": TokenType.KEYWORD,
            "true": TokenType.BOOLEAN,
            "false": TokenType.BOOLEAN,
            "null": TokenType.NULL,
            "undefined": TokenType.NULL,
            "from": TokenType.KEYWORD,
            "file": TokenType.KEYWORD,
            "minimum": TokenType.KEYWORD,
            "words": TokenType.KEYWORD,
            "canRead": TokenType.KEYWORD,
            "canWrite": TokenType.KEYWORD,
            "canCall": TokenType.KEYWORD,
        }
        
        # Initialize source code tracking
        self.source = ""
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
    
    def tokenize(self, source: str) -> List[Token]:
        """Convert source code into a list of tokens.
        
        Args:
            source: The source code to tokenize
            
        Returns:
            A list of tokens
        """
        # Reset state
        self.source = source
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        
        # Tokenize the source code
        while not self.is_at_end():
            # Start of next lexeme
            self.start = self.current
            self.scan_token()
        
        # Add EOF token
        self.tokens.append(Token(
            type=TokenType.EOF,
            lexeme="",
            line=self.line,
            column=self.column
        ))
        
        return self.tokens
    
    def is_at_end(self) -> bool:
        """Check if we've reached the end of the source code."""
        return self.current >= len(self.source)
    
    def advance(self) -> str:
        """Consume and return the next character in the source code."""
        char = self.source[self.current]
        self.current += 1
        self.column += 1
        return char
    
    def peek(self) -> str:
        """Return the current character without advancing."""
        if self.is_at_end():
            return '\0'
        return self.source[self.current]
    
    def peek_next(self) -> str:
        """Return the next character without advancing."""
        if self.current + 1 >= len(self.source):
            return '\0'
        return self.source[self.current + 1]
    
    def match(self, expected: str) -> bool:
        """Check if the next character matches the expected one.
        
        If it matches, consume the character and return True.
        Otherwise, leave it alone and return False.
        """
        if self.is_at_end() or self.source[self.current] != expected:
            return False
        
        self.current += 1
        self.column += 1
        return True
    
    def add_token(self, token_type: TokenType, value: Any = None):
        """Add a token to the list of tokens."""
        lexeme = self.source[self.start:self.current]
        self.tokens.append(Token(
            type=token_type,
            lexeme=lexeme,
            value=value,
            line=self.line,
            column=self.column - len(lexeme)
        ))
    
    def scan_token(self):
        """Scan a single token from the source code."""
        char = self.advance()
        
        # Single-character tokens
        if char == '(':
            self.add_token(TokenType.LEFT_PAREN)
        elif char == ')':
            self.add_token(TokenType.RIGHT_PAREN)
        elif char == '{':
            self.add_token(TokenType.LEFT_BRACE)
        elif char == '}':
            self.add_token(TokenType.RIGHT_BRACE)
        elif char == '[':
            self.add_token(TokenType.LEFT_BRACKET)
        elif char == ']':
            self.add_token(TokenType.RIGHT_BRACKET)
        elif char == ',':
            self.add_token(TokenType.COMMA)
        elif char == '.':
            if self.match('.'):
                self.add_token(TokenType.DOT_DOT)
            else:
                self.add_token(TokenType.DOT)
        elif char == ';':
            self.add_token(TokenType.SEMICOLON)
        elif char == ':':
            self.add_token(TokenType.COLON)
        elif char == '?':
            self.add_token(TokenType.QUESTION)
        
        # Operators that may be one or two characters
        elif char == '=':
            if self.match('='):
                self.add_token(TokenType.EQUAL)
            else:
                self.add_token(TokenType.ASSIGN)
        elif char == '!':
            if self.match('='):
                self.add_token(TokenType.NOT_EQUAL)
            else:
                self.add_token(TokenType.NOT)
        elif char == '<':
            if self.match('='):
                self.add_token(TokenType.LESS_EQUAL)
            else:
                self.add_token(TokenType.LESS)
        elif char == '>':
            if self.match('='):
                self.add_token(TokenType.GREATER_EQUAL)
            else:
                self.add_token(TokenType.GREATER)
        elif char == '+':
            if self.match('='):
                self.add_token(TokenType.PLUS_ASSIGN)
            else:
                self.add_token(TokenType.PLUS)
        elif char == '-':
            if self.match('>'):
                self.add_token(TokenType.ARROW)
            elif self.match('='):
                self.add_token(TokenType.MINUS_ASSIGN)
            else:
                self.add_token(TokenType.MINUS)
        elif char == '*':
            if self.match('='):
                self.add_token(TokenType.MULTIPLY_ASSIGN)
            else:
                self.add_token(TokenType.MULTIPLY)
        elif char == '/':
            if self.match('/'):
                # Single-line comment
                while self.peek() != '\n' and not self.is_at_end():
                    self.advance()
                self.add_token(TokenType.COMMENT)
            elif self.match('*'):
                # Multi-line comment
                while not (self.peek() == '*' and self.peek_next() == '/') and not self.is_at_end():
                    if self.peek() == '\n':
                        self.line += 1
                        self.column = 1
                    self.advance()
                
                if self.is_at_end():
                    # Unterminated comment
                    self.add_token(TokenType.ERROR, "Unterminated comment")
                else:
                    # Consume the closing */
                    self.advance()  # *
                    self.advance()  # /
                    self.add_token(TokenType.COMMENT)
            elif self.match('='):
                self.add_token(TokenType.DIVIDE_ASSIGN)
            else:
                self.add_token(TokenType.DIVIDE)
        elif char == '%':
            if self.match('='):
                self.add_token(TokenType.MODULO_ASSIGN)
            else:
                self.add_token(TokenType.MODULO)
        elif char == '&' and self.match('&'):
            self.add_token(TokenType.AND)
        elif char == '|' and self.match('|'):
            self.add_token(TokenType.OR)
            
        # Whitespace
        elif char == ' ' or char == '\r' or char == '\t':
            # Ignore whitespace
            pass
        elif char == '\n':
            self.line += 1
            self.column = 1
        
        # String literals
        elif char == '"' or char == "'":
            self.string(char)
        
        # Template strings
        elif char == '`':
            self.template_string()
        
        # Number literals
        elif char.isdigit():
            self.number()
        
        # Identifiers and keywords
        elif self.is_alpha(char):
            self.identifier()
        
        else:
            # Unrecognized character
            self.add_token(TokenType.ERROR, f"Unexpected character: {char}")
    
    def string(self, quote_char: str):
        """Process a string literal."""
        # Process characters until we reach the closing quote
        value = ""
        escape_sequence = False
        
        while not self.is_at_end():
            char = self.peek()
            
            if escape_sequence:
                # Handle escape sequences
                if char == 'n':
                    value += '\n'
                elif char == 't':
                    value += '\t'
                elif char == 'r':
                    value += '\r'
                elif char == '"':
                    value += '"'
                elif char == "'":
                    value += "'"
                elif char == '\\':
                    value += '\\'
                else:
                    # Invalid escape sequence
                    value += f"\\{char}"
                
                escape_sequence = False
                self.advance()
            elif char == '\\':
                escape_sequence = True
                self.advance()
            elif char == quote_char:
                # End of string
                break
            elif char == '\n':
                # Unterminated string
                self.add_token(TokenType.ERROR, "Unterminated string")
                return
            else:
                value += char
                self.advance()
        
        if self.is_at_end():
            # Unterminated string
            self.add_token(TokenType.ERROR, "Unterminated string")
            return
        
        # Consume the closing quote
        self.advance()
        
        # Add the string token with the processed value
        self.add_token(TokenType.STRING, value)
    
    def template_string(self):
        """Process a template string literal."""
        # Implement template string processing logic
        # This is a simplified version - a real implementation would handle embedded expressions
        value = ""
        expressions = []
        escape_sequence = False
        in_expression = False
        expression_level = 0
        expression_start = -1
        
        while not self.is_at_end():
            char = self.peek()
            
            if in_expression:
                # Inside a ${...} expression
                if char == '{':
                    expression_level += 1
                elif char == '}':
                    expression_level -= 1
                    if expression_level == 0:
                        # End of expression
                        expr_text = self.source[expression_start:self.current]
                        expressions.append(expr_text)
                        in_expression = False
                        value += "${" + expr_text + "}"
            elif escape_sequence:
                # Handle escape sequences as in regular strings
                if char == 'n':
                    value += '\n'
                elif char == 't':
                    value += '\t'
                elif char == 'r':
                    value += '\r'
                elif char == '`':
                    value += '`'
                elif char == '\$':
                    value += '\$'
                elif char == '\\':
                    value += '\\'
                else:
                    value += f"\\{char}"
                
                escape_sequence = False
            elif char == '\\':
                escape_sequence = True
            elif char == '`':
                # End of template string
                break
            elif char == '$' and self.peek_next() == '{':
                # Start of expression
                in_expression = True
                expression_level = 1
                self.advance()  # Consume $
                self.advance()  # Consume {
                expression_start = self.current
                continue
            elif char == '\n':
                # Template strings can span multiple lines
                value += '\n'
                self.line += 1
                self.column = 1
            else:
                value += char
            
            self.advance()
        
        if self.is_at_end():
            # Unterminated template string
            self.add_token(TokenType.ERROR, "Unterminated template string")
            return
        
        # Consume the closing backtick
        self.advance()
        
        # Add the template string token with the processed value and expressions
        self.add_token(TokenType.TEMPLATE_STRING, {"value": value, "expressions": expressions})
    
    def number(self):
        """Process a numeric literal."""
        # Process digits
        is_integer = True
        
        while self.peek().isdigit():
            self.advance()
        
        # Look for a decimal part
        if self.peek() == '.' and self.peek_next().isdigit():
            is_integer = False
            
            # Consume the decimal point
            self.advance()
            
            # Process decimal digits
            while self.peek().isdigit():
                self.advance()
        
        # Extract the numeric string
        num_str = self.source[self.start:self.current]
        
        # Convert to appropriate type and add token
        if is_integer:
            value = int(num_str)
            self.add_token(TokenType.INTEGER, value)
        else:
            value = float(num_str)
            self.add_token(TokenType.FLOAT, value)
    
    def identifier(self):
        """Process an identifier or keyword."""
        # Process alphanumeric characters
        while self.is_alphanumeric(self.peek()):
            self.advance()
        
        # Extract the identifier
        text = self.source[self.start:self.current]
        
        # Check if it's a keyword
        if text in self.keywords:
            token_type = self.keywords[text]
            
            # Handle special cases for true, false, null
            if token_type == TokenType.BOOLEAN:
                self.add_token(token_type, text == "true")
            elif token_type == TokenType.NULL:
                self.add_token(token_type, None)
            else:
                self.add_token(token_type, text)
        else:
            # It's a regular identifier
            self.add_token(TokenType.IDENTIFIER, text)
    
    def is_alpha(self, char: str) -> bool:
        """Check if a character is alphabetic or underscore."""
        return char.isalpha() or char == '_'
    
    def is_alphanumeric(self, char: str) -> bool:
        """Check if a character is alphanumeric or underscore."""
        return char.isalnum() or char == '_'