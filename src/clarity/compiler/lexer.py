"""
Clarity Programming Language Lexer

This module implements the lexical analysis component of the Clarity compiler,
responsible for tokenizing Clarity source code into a stream of tokens for
parsing.
"""

import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Generator, Tuple, Any


class TokenType(Enum):
    """Token types for the Clarity programming language."""
    # Keywords
    MODEL = auto()
    FUNC = auto()
    VAR = auto()
    TENSOR = auto()
    PROB = auto()
    GRAD = auto()
    IF = auto()
    ELSE = auto()
    FOR = auto()
    WHILE = auto()
    RETURN = auto()
    IMPORT = auto()
    CONCURRENT = auto()
    SELF = auto()
    NEW = auto()
    
    # AI-specific keywords
    TRAIN = auto()
    INFERENCE = auto()
    LAYERS = auto()
    FORWARD = auto()
    BACKWARD = auto()
    COMPONENTS = auto()
    
    # Types
    TYPE_INT = auto()
    TYPE_FLOAT = auto()
    TYPE_STRING = auto()
    TYPE_BOOL = auto()
    
    # Literals
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    ASSIGN = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    SEMICOLON = auto()
    ARROW = auto()
    
    # Special
    IDENTIFIER = auto()
    COMMENT = auto()
    DECORATOR = auto()
    EOF = auto()
    ERROR = auto()


@dataclass
class Token:
    """
    Represents a token in the Clarity programming language.
    
    Attributes:
        type: The type of token
        value: The string value of the token
        line: The line number where the token appears
        column: The column number where the token starts
    """
    type: TokenType
    value: str
    line: int
    column: int
    
    def __repr__(self) -> str:
        return f"Token({self.type}, '{self.value}', line={self.line}, column={self.column})"


class Lexer:
    """
    Lexical analyzer for the Clarity programming language.
    
    This class converts a stream of characters into a stream of tokens
    for parsing.
    """
    
    # Map of keywords to token types
    KEYWORDS = {
        'model': TokenType.MODEL,
        'func': TokenType.FUNC,
        'var': TokenType.VAR,
        'tensor': TokenType.TENSOR,
        'prob': TokenType.PROB,
        'grad': TokenType.GRAD,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'for': TokenType.FOR,
        'while': TokenType.WHILE,
        'return': TokenType.RETURN,
        'import': TokenType.IMPORT,
        'concurrent': TokenType.CONCURRENT,
        'self': TokenType.SELF,
        'new': TokenType.NEW,
        'train': TokenType.TRAIN,
        'inference': TokenType.INFERENCE,
        'layers': TokenType.LAYERS,
        'forward': TokenType.FORWARD,
        'backward': TokenType.BACKWARD,
        'components': TokenType.COMPONENTS,
        'int': TokenType.TYPE_INT,
        'float': TokenType.TYPE_FLOAT,
        'float32': TokenType.TYPE_FLOAT,
        'string': TokenType.TYPE_STRING,
        'bool': TokenType.TYPE_BOOL,
        'true': TokenType.BOOL,
        'false': TokenType.BOOL,
    }
    
    def __init__(self, source: str):
        """
        Initialize the lexer with the source code.
        
        Args:
            source: The source code to tokenize
        """
        self.source = source
        self.tokens: List[Token] = []
        self.position = 0
        self.line = 1
        self.column = 1
    
    def get_char(self) -> str:
        """Get the current character and advance position."""
        if self.position >= len(self.source):
            return ''
        char = self.source[self.position]
        self.position += 1
        return char
    
    def peek(self, offset: int = 0) -> str:
        """Peek at a character without advancing position."""
        pos = self.position + offset
        if pos >= len(self.source):
            return ''
        return self.source[pos]
    
    def tokenize(self) -> List[Token]:
        """
        Tokenize the source code.
        
        Returns:
            A list of tokens
        """
        while self.position < len(self.source):
            char = self.get_char()
            
            # Skip whitespace
            if char.isspace():
                if char == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                continue
            
            # Handle identifiers and keywords
            if char.isalpha() or char == '_':
                self.position -= 1  # Go back to process the full identifier
                self._tokenize_identifier()
                continue
            
            # Handle numbers
            if char.isdigit() or (char == '.' and self.peek().isdigit()):
                self.position -= 1  # Go back to process the full number
                self._tokenize_number()
                continue
            
            # Handle strings
            if char == '"' or char == "'":
                self.position -= 1  # Go back to process the full string
                self._tokenize_string()
                continue
            
            # Handle comments
            if char == '/' and self.peek() == '/':
                self.position -= 1  # Go back to process the full comment
                self._tokenize_comment()
                continue
            
            # Handle decorators
            if char == '@':
                self.position -= 1  # Go back to process the full decorator
                self._tokenize_decorator()
                continue
            
            # Handle operators and delimiters
            token_type = self._get_operator_or_delimiter(char)
            if token_type:
                self.tokens.append(Token(token_type, char, self.line, self.column))
                self.column += 1
                continue
            
            # Handle unknown characters
            self.tokens.append(Token(TokenType.ERROR, char, self.line, self.column))
            self.column += 1
        
        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        
        return self.tokens
    
    def _tokenize_identifier(self) -> None:
        """Tokenize an identifier or keyword."""
        start_col = self.column
        value = ''
        
        while self.position < len(self.source) and (self.source[self.position].isalnum() or self.source[self.position] == '_'):
            value += self.source[self.position]
            self.position += 1
            self.column += 1
        
        # Check if it's a keyword
        token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
        self.tokens.append(Token(token_type, value, self.line, start_col))
    
    def _tokenize_number(self) -> None:
        """Tokenize a number (int or float)."""
        start_col = self.column
        value = ''
        is_float = False
        
        while self.position < len(self.source) and (self.source[self.position].isdigit() or self.source[self.position] == '.'):
            if self.source[self.position] == '.':
                if is_float:  # Second decimal point is not allowed
                    break
                is_float = True
            
            value += self.source[self.position]
            self.position += 1
            self.column += 1
        
        token_type = TokenType.FLOAT if is_float else TokenType.INT
        self.tokens.append(Token(token_type, value, self.line, start_col))
    
    def _tokenize_string(self) -> None:
        """Tokenize a string literal."""
        start_col = self.column
        quote = self.source[self.position]
        value = quote
        self.position += 1
        self.column += 1
        
        while self.position < len(self.source) and self.source[self.position] != quote:
            # Handle escape sequences
            if self.source[self.position] == '\\' and self.position + 1 < len(self.source):
                value += self.source[self.position:self.position+2]
                self.position += 2
                self.column += 2
            else:
                value += self.source[self.position]
                if self.source[self.position] == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.position += 1
        
        # Add closing quote if found
        if self.position < len(self.source):
            value += self.source[self.position]
            self.position += 1
            self.column += 1
        
        self.tokens.append(Token(TokenType.STRING, value, self.line, start_col))
    
    def _tokenize_comment(self) -> None:
        """Tokenize a single-line comment."""
        start_col = self.column
        value = ''
        
        # Skip the initial '//'
        self.position += 2
        self.column += 2
        value = '//'
        
        # Read until end of line
        while self.position < len(self.source) and self.source[self.position] != '\n':
            value += self.source[self.position]
            self.position += 1
            self.column += 1
        
        self.tokens.append(Token(TokenType.COMMENT, value, self.line, start_col))
    
    def _tokenize_decorator(self) -> None:
        """Tokenize a decorator."""
        start_col = self.column
        value = '@'
        self.position += 1
        self.column += 1
        
        # Read the decorator name
        while self.position < len(self.source) and (self.source[self.position].isalnum() or self.source[self.position] == '_'):
            value += self.source[self.position]
            self.position += 1
            self.column += 1
        
        self.tokens.append(Token(TokenType.DECORATOR, value, self.line, start_col))
    
    def _get_operator_or_delimiter(self, char: str) -> Optional[TokenType]:
        """Map a character to its operator or delimiter token type."""
        mapping = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.MULTIPLY,
            '/': TokenType.DIVIDE,
            '=': TokenType.ASSIGN,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            ',': TokenType.COMMA,
            '.': TokenType.DOT,
            ':': TokenType.COLON,
            ';': TokenType.SEMICOLON,
            '!': TokenType.NOT,
        }
        
        # Handle multi-character operators
        if char == '=' and self.peek() == '=':
            self.position += 1
            self.column += 1
            return TokenType.EQ
        elif char == '!' and self.peek() == '=':
            self.position += 1
            self.column += 1
            return TokenType.NEQ
        elif char == '<' and self.peek() == '=':
            self.position += 1
            self.column += 1
            return TokenType.LTE
        elif char == '>' and self.peek() == '=':
            self.position += 1
            self.column += 1
            return TokenType.GTE
        elif char == '-' and self.peek() == '>':
            self.position += 1
            self.column += 1
            return TokenType.ARROW
        elif char == '&' and self.peek() == '&':
            self.position += 1
            self.column += 1
            return TokenType.AND
        elif char == '|' and self.peek() == '|':
            self.position += 1
            self.column += 1
            return TokenType.OR
        elif char == '<':
            return TokenType.LT
        elif char == '>':
            return TokenType.GT
        
        return mapping.get(char)


def tokenize(source: str) -> List[Token]:
    """
    Convenience function to tokenize Clarity source code.
    
    Args:
        source: The source code to tokenize
        
    Returns:
        A list of tokens
    """
    lexer = Lexer(source)
    return lexer.tokenize()
