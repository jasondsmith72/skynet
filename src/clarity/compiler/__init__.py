"""
Clarity Programming Language Compiler

This package contains the core components of the Clarity compiler.
"""

from .lexer import tokenize, Token, TokenType
from .parser import parse
from .semantic_analyzer import SemanticAnalyzer, SemanticError
import parser_expressions  # This will apply the extensions to the Parser class

__all__ = [
    'tokenize', 'Token', 'TokenType', 
    'parse',
    'SemanticAnalyzer', 'SemanticError'
]
