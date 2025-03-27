"""
Clarity Programming Language Parser - Statement Parsing

This module implements the statement parsing components of the Clarity parser.
"""

from typing import List, Optional, Any
from .lexer import Token, TokenType
from .ast import *
from .parser import Parser, ParseError

def add_statement_parsers(cls):
    """
    Add statement parsing methods to the Parser class.
    
    This function extends the Parser class with methods for parsing statements.
    
    Args:
        cls: The Parser class to extend
    
    Returns:
        The extended Parser class
    """
    
    def parse_statement(self) -> Statement:
        """Parse a single statement."""
        if self.match(TokenType.VAR):
            return self.parse_variable_declaration()
        elif self.match(TokenType.IF):
            return self.parse_if_statement()
        elif self.match(TokenType.WHILE):
            return self.parse_while_loop()
        elif self.match(TokenType.FOR):
            return self.parse_for_loop() # Placeholder
        elif self.match(TokenType.RETURN):
            return self.parse_return_statement()
        elif self.match(TokenType.LBRACE):
            return self.parse_block()
        elif self.match(TokenType.IMPORT):
             # Already handled in main parse loop, but keep for potential future use
             # or if called from other contexts. For now, raise error or skip.
             self.error(self.previous(), "Import statement found outside of top level.")
             self.synchronize() # Attempt to recover
             return None # Or a specific error node if defined
        elif self.match(TokenType.FUNC):
             # Already handled in main parse loop
             self.error(self.previous(), "Function definition found outside of top level.")
             self.synchronize()
             return None
        elif self.match(TokenType.MODEL):
             # Already handled in main parse loop
             self.error(self.previous(), "Model definition found outside of top level.")
             self.synchronize()
             return None
        else:
            # Default to expression statement
            return self.parse_expression_statement()

    def parse_block(self) -> Block:
        """Parse a block of statements enclosed in curly braces."""
        statements = []
        start_token = self.previous() # The opening LBRACE
        
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
                
        self.consume(TokenType.RBRACE, "Expected '}' after block.")
        return Block(statements, start_token.line, start_token.column)

    def parse_variable_declaration(self) -> VariableDeclaration:
        """Parse a variable declaration: var name: type = initializer;"""
        start_token = self.previous() # The 'var' token
        name_token = self.consume(TokenType.IDENTIFIER, "Expected variable name.")
        name = Identifier(name_token.value, name_token.line, name_token.column)
        
        type_annotation: Optional[TypeAnnotation] = None
        if self.match(TokenType.COLON):
            type_annotation = self.parse_type_annotation() # Placeholder
            
        initializer: Optional[Expression] = None
        if self.match(TokenType.ASSIGN):
            initializer = self.parse_expression()
            
        self.consume(TokenType.SEMICOLON, "Expected ';' after variable declaration.")
        return VariableDeclaration(name, type_annotation, initializer, start_token.line, start_token.column)

    def parse_if_statement(self) -> IfStatement:
        """Parse an if statement: if (condition) then_block [else else_block]"""
        start_token = self.previous() # The 'if' token
        self.consume(TokenType.LPAREN, "Expected '(' after 'if'.")
        condition = self.parse_expression()
        self.consume(TokenType.RPAREN, "Expected ')' after if condition.")
        
        then_block = self.parse_block()
        
        else_block: Optional[Block] = None
        if self.match(TokenType.ELSE):
            else_block = self.parse_block()
            
        return IfStatement(condition, then_block, else_block, start_token.line, start_token.column)

    def parse_while_loop(self) -> WhileLoop:
        """Parse a while loop: while (condition) body_block"""
        start_token = self.previous() # The 'while' token
        self.consume(TokenType.LPAREN, "Expected '(' after 'while'.")
        condition = self.parse_expression()
        self.consume(TokenType.RPAREN, "Expected ')' after while condition.")
        
        body = self.parse_block()
        
        return WhileLoop(condition, body, start_token.line, start_token.column)

    def parse_for_loop(self) -> ForLoop:
        """Parse a for loop: for (initializer; condition; update) body_block"""
        # Placeholder implementation
        start_token = self.previous() # The 'for' token
        self.consume(TokenType.LPAREN, "Expected '(' after 'for'.")
        
        initializer: Optional[Statement] = None
        if not self.check(TokenType.SEMICOLON):
            if self.match(TokenType.VAR):
                initializer = self.parse_variable_declaration() # Reuses var parsing
            else:
                initializer = self.parse_expression_statement() # Allows expression like i = 0
        else:
             self.consume(TokenType.SEMICOLON, "Expected ';' after for initializer.") # Consume the semicolon if initializer is empty

        condition: Optional[Expression] = None
        if not self.check(TokenType.SEMICOLON):
            condition = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after for loop condition.")

        update: Optional[Statement] = None
        if not self.check(TokenType.RPAREN):
             # For update, we expect an expression, typically assignment or increment/decrement
             # We wrap it in an ExpressionStatement
             update_expr = self.parse_expression()
             update = ExpressionStatement(update_expr, update_expr.line, update_expr.column)
             
        self.consume(TokenType.RPAREN, "Expected ')' after for clauses.")
        
        body = self.parse_block()
        
        return ForLoop(initializer, condition, update, body, start_token.line, start_token.column)

    def parse_return_statement(self) -> ReturnStatement:
        """Parse a return statement: return [value];"""
        start_token = self.previous() # The 'return' token
        value: Optional[Expression] = None
        if not self.check(TokenType.SEMICOLON):
            value = self.parse_expression()
            
        self.consume(TokenType.SEMICOLON, "Expected ';' after return value.")
        return ReturnStatement(value, start_token.line, start_token.column)

    def parse_expression_statement(self) -> ExpressionStatement:
        """Parse an expression statement: expression;"""
        expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after expression.")
        return ExpressionStatement(expr, expr.line, expr.column)

    def parse_import(self) -> ImportStatement:
        """Parse an import statement: import module [as alias]; or import module.{elem1, elem2};"""
        # Basic implementation - needs refinement for aliases and specific elements
        start_token = self.previous() # The 'import' token
        module_token = self.consume(TokenType.IDENTIFIER, "Expected module name.")
        module = Identifier(module_token.value, module_token.line, module_token.column)
        
        # TODO: Add support for 'as alias' and '.{elements}'
        elements = [] 
        
        self.consume(TokenType.SEMICOLON, "Expected ';' after import statement.")
        return ImportStatement(module, elements, start_token.line, start_token.column)

    def parse_function(self) -> FunctionDeclaration:
        """Parse a function declaration: func name(params) -> return_type { body }"""
        # Placeholder implementation
        start_token = self.previous() # The 'func' token
        name_token = self.consume(TokenType.IDENTIFIER, "Expected function name.")
        name = Identifier(name_token.value, name_token.line, name_token.column)
        
        self.consume(TokenType.LPAREN, "Expected '(' after function name.")
        parameters = self.parse_parameter_list() # Placeholder
        self.consume(TokenType.RPAREN, "Expected ')' after parameters.")
        
        return_type: Optional[TypeAnnotation] = None
        if self.match(TokenType.ARROW):
            return_type = self.parse_type_annotation() # Placeholder
            
        body = self.parse_block()
        
        # TODO: Parse decorators if needed
        decorators = []
        
        return FunctionDeclaration(name, parameters, return_type, body, decorators, start_token.line, start_token.column)

    def parse_model(self) -> ModelDeclaration:
        """Parse a model declaration: model name { layers; components; forward; train; }"""
        # Placeholder implementation - complex structure
        start_token = self.previous() # The 'model' token
        name_token = self.consume(TokenType.IDENTIFIER, "Expected model name.")
        name = Identifier(name_token.value, name_token.line, name_token.column)
        
        self.consume(TokenType.LBRACE, "Expected '{' before model body.")
        
        layers = []
        components = []
        forward_pass = None
        train_method = None
        
        # TODO: Implement parsing for layers, components, forward, train blocks
        # Example structure (needs proper parsing logic):
        # while not self.check(TokenType.RBRACE) and not self.is_at_end():
        #     if self.match(TokenType.LAYERS):
        #         # parse layers block
        #     elif self.match(TokenType.COMPONENTS):
        #         # parse components block
        #     elif self.match(TokenType.FORWARD):
        #         # parse forward pass
        #     elif self.match(TokenType.TRAIN):
        #         # parse train method
        #     else:
        #         self.error(self.peek(), "Expected 'layers', 'components', 'forward', or 'train' in model body.")
        #         self.advance()

        self.consume(TokenType.RBRACE, "Expected '}' after model body.")
        
        # TODO: Parse decorators if needed
        decorators = []

        # Use default ForwardPassDefinition until properly parsed
        if forward_pass is None:
             forward_pass = ForwardPassDefinition(line=start_token.line, column=start_token.column)

        return ModelDeclaration(name, layers, components, forward_pass, train_method, decorators, start_token.line, start_token.column)

    def parse_parameter_list(self) -> List[Parameter]:
        """Parse a list of parameters: (name: type, name: type = default, ...)"""
        # Placeholder implementation
        parameters = []
        if not self.check(TokenType.RPAREN):
            # TODO: Implement full parameter parsing with types and defaults
            pass 
        return parameters

    def parse_type_annotation(self) -> TypeAnnotation:
        """Parse a type annotation: int, float, string, bool, tensor[type, shape], prob[type], grad[type]"""
        # Placeholder implementation
        if self.match(TokenType.TYPE_INT):
            return SimpleType("int", self.previous().line, self.previous().column)
        elif self.match(TokenType.TYPE_FLOAT):
             return SimpleType("float", self.previous().line, self.previous().column)
        elif self.match(TokenType.TYPE_STRING):
             return SimpleType("string", self.previous().line, self.previous().column)
        elif self.match(TokenType.TYPE_BOOL):
             return SimpleType("bool", self.previous().line, self.previous().column)
        # TODO: Add parsing for TENSOR, PROB, GRAD types
        else:
            name_token = self.consume(TokenType.IDENTIFIER, "Expected type name.")
            # Assume simple type for now if identifier is found
            return SimpleType(name_token.value, name_token.line, name_token.column)

    # Add the methods to the class
    cls.parse_statement = parse_statement
    cls.parse_block = parse_block
    cls.parse_variable_declaration = parse_variable_declaration
    cls.parse_if_statement = parse_if_statement
    cls.parse_while_loop = parse_while_loop
    cls.parse_for_loop = parse_for_loop
    cls.parse_return_statement = parse_return_statement
    cls.parse_expression_statement = parse_expression_statement
    cls.parse_import = parse_import # Add even if handled at top level
    cls.parse_function = parse_function # Add even if handled at top level
    cls.parse_model = parse_model # Add even if handled at top level
    cls.parse_parameter_list = parse_parameter_list
    cls.parse_type_annotation = parse_type_annotation
    
    return cls

# Apply the extension to the Parser class
import sys
from .parser import Parser
add_statement_parsers(Parser)
