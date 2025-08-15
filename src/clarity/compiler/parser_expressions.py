"""
Clarity Programming Language Parser - Expression Parsing

This module implements the expression parsing components of the Clarity parser.
"""

from typing import List, Optional, Any
from .lexer import Token, TokenType
from .ast import *
from .parser import Parser, ParseError


def add_expression_parsers(cls):
    """
    Add expression parsing methods to the Parser class.
    
    This function extends the Parser class with methods for parsing expressions.
    
    Args:
        cls: The Parser class to extend
    
    Returns:
        The extended Parser class
    """
    
    def parse_expression(self) -> Expression:
        """Parse an expression."""
        return self.parse_assignment()
    
    def parse_assignment(self) -> Expression:
        """Parse an assignment expression."""
        expr = self.parse_logical_or()
        
        if self.match(TokenType.ASSIGN):
            equals = self.previous()
            value = self.parse_assignment()
            
            if isinstance(expr, VariableReference):
                return Assignment(target=expr, value=value, line=equals.line, column=equals.column)
            elif isinstance(expr, MemberAccess):
                return Assignment(target=expr, value=value, line=equals.line, column=equals.column)
            elif isinstance(expr, ArrayAccess):
                return Assignment(target=expr, value=value, line=equals.line, column=equals.column)
            
            self.error(equals, "Invalid assignment target.")
        
        return expr
    
    def parse_logical_or(self) -> Expression:
        """Parse a logical OR expression."""
        expr = self.parse_logical_and()
        
        while self.match(TokenType.OR):
            operator = self.previous().value
            right = self.parse_logical_and()
            expr = BinaryOperation(left=expr, operator=operator, right=right, line=expr.line, column=expr.column)
        
        return expr
    
    def parse_logical_and(self) -> Expression:
        """Parse a logical AND expression."""
        expr = self.parse_equality()
        
        while self.match(TokenType.AND):
            operator = self.previous().value
            right = self.parse_equality()
            expr = BinaryOperation(left=expr, operator=operator, right=right, line=expr.line, column=expr.column)
        
        return expr
    
    def parse_equality(self) -> Expression:
        """Parse an equality expression."""
        expr = self.parse_comparison()
        
        while self.match(TokenType.EQ, TokenType.NEQ):
            operator = self.previous().value
            right = self.parse_comparison()
            expr = BinaryOperation(left=expr, operator=operator, right=right, line=expr.line, column=expr.column)
        
        return expr
    
    def parse_comparison(self) -> Expression:
        """Parse a comparison expression."""
        expr = self.parse_term()
        
        while self.match(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            operator = self.previous().value
            right = self.parse_term()
            expr = BinaryOperation(left=expr, operator=operator, right=right, line=expr.line, column=expr.column)
        
        return expr
    
    def parse_term(self) -> Expression:
        """Parse a term expression (addition, subtraction)."""
        expr = self.parse_factor()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            operator = self.previous().value
            right = self.parse_factor()
            expr = BinaryOperation(left=expr, operator=operator, right=right, line=expr.line, column=expr.column)
        
        return expr
    
    def parse_factor(self) -> Expression:
        """Parse a factor expression (multiplication, division)."""
        expr = self.parse_unary()
        
        while self.match(TokenType.MULTIPLY, TokenType.DIVIDE):
            operator = self.previous().value
            right = self.parse_unary()
            expr = BinaryOperation(left=expr, operator=operator, right=right, line=expr.line, column=expr.column)
        
        return expr
    
    def parse_unary(self) -> Expression:
        """Parse a unary expression."""
        if self.match(TokenType.MINUS, TokenType.NOT):
            operator = self.previous().value
            right = self.parse_unary()
            return UnaryOperation(operator=operator, operand=right, line=right.line, column=right.column)
        
        return self.parse_call()
    
    def parse_call(self) -> Expression:
        """Parse a function or method call expression."""
        expr = self.parse_primary()
        
        while True:
            if self.match(TokenType.LPAREN):
                # Function or model call
                expr = self.finish_call(expr)
            elif self.match(TokenType.DOT):
                # Member access
                name_token = self.consume(TokenType.IDENTIFIER, "Expected property name after '.'")
                name = Identifier(name=name_token.value, line=name_token.line, column=name_token.column)
                expr = MemberAccess(object=expr, member=name, line=expr.line, column=expr.column)
            elif self.match(TokenType.LBRACKET):
                # Array/tensor access
                indices = []
                if not self.check(TokenType.RBRACKET):
                    indices.append(self.parse_expression())
                    
                    while self.match(TokenType.COMMA):
                        indices.append(self.parse_expression())
                
                close_token = self.consume(TokenType.RBRACKET, "Expected ']' after array indices")
                expr = ArrayAccess(array=expr, indices=indices, line=expr.line, column=expr.column)
            else:
                break
        
        return expr
    
    def finish_call(self, callee: Expression) -> Expression:
        """Finish parsing a function or model call."""
        arguments = []
        
        if not self.check(TokenType.RPAREN):
            arguments.append(self.parse_expression())
            
            while self.match(TokenType.COMMA):
                arguments.append(self.parse_expression())
        
        paren = self.consume(TokenType.RPAREN, "Expected ')' after arguments")
        
        # Determine if this is a model call or regular function call
        if isinstance(callee, MemberAccess) and callee.member.name == "new":
            # Handle model creation with .new()
            return ModelCall(model=callee.object, inputs=arguments, line=callee.line, column=callee.column)
        elif isinstance(callee, VariableReference) and callee.name.name in self.get_model_names():
            # Direct call to a model
            return ModelCall(model=callee, inputs=arguments, line=callee.line, column=callee.column)
        else:
            # Regular function call
            return FunctionCall(function=callee, arguments=arguments, line=callee.line, column=callee.column)
    
    def get_model_names(self) -> List[str]:
        """Get a list of model names defined in the current program."""
        # This is a simplified version; a real implementation would track declarations
        return []
    
    def parse_primary(self) -> Expression:
        """Parse a primary expression."""
        if self.match(TokenType.INT):
            value = int(self.previous().value)
            return IntLiteral(value, self.previous().line, self.previous().column)
        
        if self.match(TokenType.FLOAT):
            value = float(self.previous().value)
            return FloatLiteral(value, self.previous().line, self.previous().column)
        
        if self.match(TokenType.STRING):
            # Strip the quotes
            value = self.previous().value[1:-1]
            return StringLiteral(value, self.previous().line, self.previous().column)
        
        if self.match(TokenType.BOOL):
            value = self.previous().value == "true"
            return BoolLiteral(value, self.previous().line, self.previous().column)
        
        if self.match(TokenType.IDENTIFIER):
            name = Identifier(name=self.previous().value, line=self.previous().line, column=self.previous().column)
            return VariableReference(name=name, line=name.line, column=name.column)
        
        if self.match(TokenType.SELF):
            name = Identifier("self", self.previous().line, self.previous().column)
            return VariableReference(name, name.line, name.column)
        
        if self.match(TokenType.LPAREN):
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN, "Expected ')' after expression")
            return expr
        
        if self.match(TokenType.NEW):
            # Model instantiation with 'new'
            model_token = self.consume(TokenType.IDENTIFIER, "Expected model name after 'new'")
            model_name = Identifier(model_token.value, model_token.line, model_token.column)
            model_ref = VariableReference(model_name, model_name.line, model_name.column)
            
            self.consume(TokenType.LPAREN, "Expected '(' after model name")
            arguments = []
            
            if not self.check(TokenType.RPAREN):
                arguments.append(self.parse_expression())
                
                while self.match(TokenType.COMMA):
                    arguments.append(self.parse_expression())
            
            self.consume(TokenType.RPAREN, "Expected ')' after arguments")
            
            return ModelCall(model_ref, arguments, model_token.line, model_token.column)
        
        # Error case
        token = self.peek()
        raise self.error(token, "Expected expression")
    
    # Add the methods to the class
    cls.parse_expression = parse_expression
    cls.parse_assignment = parse_assignment
    cls.parse_logical_or = parse_logical_or
    cls.parse_logical_and = parse_logical_and
    cls.parse_equality = parse_equality
    cls.parse_comparison = parse_comparison
    cls.parse_term = parse_term
    cls.parse_factor = parse_factor
    cls.parse_unary = parse_unary
    cls.parse_call = parse_call
    cls.finish_call = finish_call
    cls.get_model_names = get_model_names
    cls.parse_primary = parse_primary
    
    return cls


# Apply the extension to the Parser class
import sys
from .parser import Parser
add_expression_parsers(Parser)
