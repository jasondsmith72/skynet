"""
Clarity Programming Language Parser - Statement Parsing

This module implements the statement parsing components of the Clarity parser.
"""

from typing import List, Optional, Any, Union
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
        # Check for decorators first
        decorators = []
        while self.check(TokenType.DECORATOR):
            decorators.append(self.advance().value)
            
        if self.match(TokenType.VAR):
            if decorators:
                 self.error(self.previous(), "Decorators are not allowed on variable declarations.")
            return self.parse_variable_declaration()
        elif self.match(TokenType.IF):
            if decorators:
                 self.error(self.previous(), "Decorators are not allowed on if statements.")
            return self.parse_if_statement()
        elif self.match(TokenType.WHILE):
            if decorators:
                 self.error(self.previous(), "Decorators are not allowed on while loops.")
            return self.parse_while_loop()
        elif self.match(TokenType.FOR):
            if decorators:
                 self.error(self.previous(), "Decorators are not allowed on for loops.")
            return self.parse_for_loop()
        elif self.match(TokenType.RETURN):
            if decorators:
                 self.error(self.previous(), "Decorators are not allowed on return statements.")
            return self.parse_return_statement()
        elif self.match(TokenType.LBRACE):
            if decorators:
                 self.error(self.previous(), "Decorators are not allowed on blocks.")
            return self.parse_block()
        elif self.match(TokenType.IMPORT):
             # Already handled in main parse loop
             self.error(self.previous(), "Import statement found outside of top level.")
             self.synchronize()
             return None
        elif self.match(TokenType.FUNC):
             # Pass decorators to parse_function
             return self.parse_function(decorators)
        elif self.match(TokenType.MODEL):
             # Pass decorators to parse_model
             return self.parse_model(decorators)
        else:
            if decorators:
                 self.error(self.peek(), "Decorators can only be applied to functions or models.")
            # Default to expression statement
            return self.parse_expression_statement()

    def parse_block(self) -> Block:
        """Parse a block of statements enclosed in curly braces."""
        statements = []
        # If called directly (e.g. for if/else/loop body), previous() might not be LBRACE
        # If called via parse_statement, previous() IS LBRACE
        start_token = self.previous() if self.previous().type == TokenType.LBRACE else self.peek() 
        
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
            type_annotation = self.parse_type_annotation()
            
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
        
        # Need to check for LBRACE for the block
        self.consume(TokenType.LBRACE, "Expected '{' to start if block.")
        then_block = self.parse_block()
        
        else_block: Optional[Block] = None
        if self.match(TokenType.ELSE):
            # Need to check for LBRACE for the else block
            self.consume(TokenType.LBRACE, "Expected '{' to start else block.")
            else_block = self.parse_block()
            
        return IfStatement(condition, then_block, else_block, start_token.line, start_token.column)

    def parse_while_loop(self) -> WhileLoop:
        """Parse a while loop: while (condition) body_block"""
        start_token = self.previous() # The 'while' token
        self.consume(TokenType.LPAREN, "Expected '(' after 'while'.")
        condition = self.parse_expression()
        self.consume(TokenType.RPAREN, "Expected ')' after while condition.")
        
        # Need to check for LBRACE for the block
        self.consume(TokenType.LBRACE, "Expected '{' to start while block.")
        body = self.parse_block()
        
        return WhileLoop(condition, body, start_token.line, start_token.column)

    def parse_for_loop(self) -> ForLoop:
        """Parse a for loop: for (initializer; condition; update) body_block"""
        start_token = self.previous() # The 'for' token
        self.consume(TokenType.LPAREN, "Expected '(' after 'for'.")
        
        initializer: Optional[Statement] = None
        if not self.check(TokenType.SEMICOLON):
            if self.match(TokenType.VAR):
                 # Need to backtrack 'var' since parse_variable_declaration expects it
                 self.current -= 1 
                 initializer = self.parse_variable_declaration()
            else:
                initializer = self.parse_expression_statement()
        else:
             self.consume(TokenType.SEMICOLON, "Expected ';' after for initializer.")

        condition: Optional[Expression] = None
        if not self.check(TokenType.SEMICOLON):
            condition = self.parse_expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after for loop condition.")

        update: Optional[Statement] = None
        if not self.check(TokenType.RPAREN):
             update_expr = self.parse_expression()
             # Wrap the update expression in a statement
             update = ExpressionStatement(update_expr, update_expr.line, update_expr.column)
             
        self.consume(TokenType.RPAREN, "Expected ')' after for clauses.")
        
        # Need to check for LBRACE for the block
        self.consume(TokenType.LBRACE, "Expected '{' to start for block.")
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
        # This method is primarily for potential future use if imports are allowed elsewhere.
        # Top-level parsing happens in Parser.parse()
        start_token = self.previous() # The 'import' token
        module_token = self.consume(TokenType.IDENTIFIER, "Expected module name.")
        module = Identifier(module_token.value, module_token.line, module_token.column)
        
        # TODO: Add support for 'as alias' and '.{elements}'
        elements = [] 
        
        self.consume(TokenType.SEMICOLON, "Expected ';' after import statement.")
        return ImportStatement(module, elements, start_token.line, start_token.column)

    def parse_function(self, decorators: List[str]) -> FunctionDeclaration:
        """Parse a function declaration: [decorators] func name(params) -> return_type { body }"""
        start_token = self.previous() # The 'func' token
        name_token = self.consume(TokenType.IDENTIFIER, "Expected function name.")
        name = Identifier(name_token.value, name_token.line, name_token.column)
        
        self.consume(TokenType.LPAREN, "Expected '(' after function name.")
        parameters = self.parse_parameter_list()
        self.consume(TokenType.RPAREN, "Expected ')' after parameters.")
        
        return_type: Optional[TypeAnnotation] = None
        if self.match(TokenType.ARROW):
            return_type = self.parse_type_annotation()
            
        self.consume(TokenType.LBRACE, "Expected '{' before function body.")
        body = self.parse_block()
                
        return FunctionDeclaration(name, parameters, return_type, body, decorators, start_token.line, start_token.column)

    def parse_model(self, decorators: List[str]) -> ModelDeclaration:
        """Parse a model declaration: [decorators] model name { layers; components; forward; train; }"""
        start_token = self.previous() # The 'model' token
        name_token = self.consume(TokenType.IDENTIFIER, "Expected model name.")
        name = Identifier(name_token.value, name_token.line, name_token.column)
        
        self.consume(TokenType.LBRACE, "Expected '{' before model body.")
        
        layers = []
        components = []
        forward_pass = None
        train_method = None
        
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            if self.match(TokenType.LAYERS):
                layers = self.parse_layers_block()
                self.consume(TokenType.SEMICOLON, "Expected ';' after layers block.")
            elif self.match(TokenType.COMPONENTS):
                components = self.parse_components_block()
                self.consume(TokenType.SEMICOLON, "Expected ';' after components block.")
            elif self.match(TokenType.FORWARD):
                if forward_pass is not None:
                    self.error(self.previous(), "Duplicate 'forward' block found in model.")
                forward_pass = self.parse_forward_pass()
                # Forward pass block ends with '}', no semicolon needed here
            elif self.match(TokenType.TRAIN):
                if train_method is not None:
                    self.error(self.previous(), "Duplicate 'train' block found in model.")
                train_method = self.parse_train_method()
                # Train method block ends with '}', no semicolon needed here
            else:
                self.error(self.peek(), "Expected 'layers', 'components', 'forward', or 'train' in model body.")
                self.synchronize() # Attempt to recover

        self.consume(TokenType.RBRACE, "Expected '}' after model body.")
        
        # Ensure forward pass is defined
        if forward_pass is None:
             # Create a default/empty one if needed, or raise error
             # forward_pass = ForwardPassDefinition(line=start_token.line, column=start_token.column)
             raise self.error(name_token, "Model must contain a 'forward' block.")

        return ModelDeclaration(name, layers, components, forward_pass, train_method, decorators, start_token.line, start_token.column)

    def parse_layers_block(self) -> List[LayerDefinition]:
        """Parse the layers block: layers { name: Type(args...); ... }"""
        layers = []
        self.consume(TokenType.LBRACE, "Expected '{' after 'layers' keyword.")
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            layer_name_token = self.consume(TokenType.IDENTIFIER, "Expected layer name.")
            layer_name = Identifier(layer_name_token.value, layer_name_token.line, layer_name_token.column)
            
            self.consume(TokenType.COLON, "Expected ':' after layer name.")
            
            layer_type_token = self.consume(TokenType.IDENTIFIER, "Expected layer type (e.g., Dense, Conv2D).")
            layer_type = Identifier(layer_type_token.value, layer_type_token.line, layer_type_token.column)
            
            self.consume(TokenType.LPAREN, "Expected '(' after layer type.")
            arguments = []
            if not self.check(TokenType.RPAREN):
                arguments.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    arguments.append(self.parse_expression())
            self.consume(TokenType.RPAREN, "Expected ')' after layer arguments.")
            
            self.consume(TokenType.SEMICOLON, "Expected ';' after layer definition.")
            layers.append(LayerDefinition(layer_name, layer_type, arguments, layer_name_token.line, layer_name_token.column))
            
        self.consume(TokenType.RBRACE, "Expected '}' after layers block.")
        return layers

    def parse_components_block(self) -> List[LayerDefinition]:
        """Parse the components block (similar structure to layers): components { name: ModelType(args...); ... }"""
        # For now, reuses LayerDefinition structure. Might need a ComponentDefinition later.
        components = []
        self.consume(TokenType.LBRACE, "Expected '{' after 'components' keyword.")
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            comp_name_token = self.consume(TokenType.IDENTIFIER, "Expected component name.")
            comp_name = Identifier(comp_name_token.value, comp_name_token.line, comp_name_token.column)
            
            self.consume(TokenType.COLON, "Expected ':' after component name.")
            
            comp_type_token = self.consume(TokenType.IDENTIFIER, "Expected component model type.")
            comp_type = Identifier(comp_type_token.value, comp_type_token.line, comp_type_token.column)
            
            self.consume(TokenType.LPAREN, "Expected '(' after component type.")
            arguments = []
            if not self.check(TokenType.RPAREN):
                arguments.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    arguments.append(self.parse_expression())
            self.consume(TokenType.RPAREN, "Expected ')' after component arguments.")
            
            self.consume(TokenType.SEMICOLON, "Expected ';' after component definition.")
            # Using LayerDefinition for now
            components.append(LayerDefinition(comp_name, comp_type, arguments, comp_name_token.line, comp_name_token.column))
            
        self.consume(TokenType.RBRACE, "Expected '}' after components block.")
        return components

    def parse_forward_pass(self) -> ForwardPassDefinition:
        """Parse the forward pass block: forward(params) -> return_type { body }"""
        start_token = self.previous() # The 'forward' token
        self.consume(TokenType.LPAREN, "Expected '(' after 'forward'.")
        parameters = self.parse_parameter_list()
        self.consume(TokenType.RPAREN, "Expected ')' after forward parameters.")
        
        return_type: Optional[TypeAnnotation] = None
        if self.match(TokenType.ARROW):
            return_type = self.parse_type_annotation()
            
        self.consume(TokenType.LBRACE, "Expected '{' before forward pass body.")
        body = self.parse_block()
        
        return ForwardPassDefinition(parameters, return_type, body, start_token.line, start_token.column)

    def parse_train_method(self) -> FunctionDeclaration:
        """Parse the optional train method block: train(params) -> return_type { body }"""
        # Structure is identical to a function declaration
        start_token = self.previous() # The 'train' token
        name = Identifier("train", start_token.line, start_token.column) # Fixed name
        
        self.consume(TokenType.LPAREN, "Expected '(' after 'train'.")
        parameters = self.parse_parameter_list()
        self.consume(TokenType.RPAREN, "Expected ')' after train parameters.")
        
        return_type: Optional[TypeAnnotation] = None
        if self.match(TokenType.ARROW):
            return_type = self.parse_type_annotation()
            
        self.consume(TokenType.LBRACE, "Expected '{' before train method body.")
        body = self.parse_block()
        
        # Train method cannot have decorators
        decorators = [] 
        
        return FunctionDeclaration(name, parameters, return_type, body, decorators, start_token.line, start_token.column)

    def parse_parameter_list(self) -> List[Parameter]:
        """Parse a list of parameters: (name: type, name: type = default, ...)"""
        parameters = []
        if not self.check(TokenType.RPAREN):
            while True:
                param_token = self.consume(TokenType.IDENTIFIER, "Expected parameter name.")
                param_name = Identifier(param_token.value, param_token.line, param_token.column)
                
                param_type: Optional[TypeAnnotation] = None
                if self.match(TokenType.COLON):
                    param_type = self.parse_type_annotation()
                    
                default_value: Optional[Expression] = None
                if self.match(TokenType.ASSIGN):
                    default_value = self.parse_expression()
                    
                parameters.append(Parameter(param_name, param_type, default_value, param_token.line, param_token.column))
                
                if not self.match(TokenType.COMMA):
                    break # Exit loop if no comma follows
                    
        return parameters

    def parse_type_annotation(self) -> TypeAnnotation:
        """Parse a type annotation: int, float, string, bool, tensor[type, shape], prob[type], grad[type]"""
        start_token = self.peek()
        
        if self.match(TokenType.TYPE_INT):
            return SimpleType("int", start_token.line, start_token.column)
        elif self.match(TokenType.TYPE_FLOAT):
            return SimpleType("float", start_token.line, start_token.column)
        elif self.match(TokenType.TYPE_STRING):
            return SimpleType("string", start_token.line, start_token.column)
        elif self.match(TokenType.TYPE_BOOL):
            return SimpleType("bool", start_token.line, start_token.column)
        elif self.match(TokenType.TENSOR):
            self.consume(TokenType.LBRACKET, "Expected '[' after 'tensor'.")
            element_type = self.parse_type_annotation()
            shape: List[Union[int, str]] = []
            # Check if shape is provided
            if self.match(TokenType.COMMA):
                while True:
                    if self.check(TokenType.INT):
                        dim_token = self.advance()
                        shape.append(int(dim_token.value))
                    elif self.check(TokenType.IDENTIFIER):
                        # Allow identifiers for dynamic shapes (e.g., 'batch_size')
                        dim_token = self.advance()
                        shape.append(dim_token.value)
                    else:
                        self.error(self.peek(), "Expected integer literal or identifier for tensor dimension.")
                        # Attempt recovery by skipping until comma or bracket
                        while not self.check(TokenType.COMMA) and not self.check(TokenType.RBRACKET) and not self.is_at_end():
                            self.advance()
                    if not self.match(TokenType.COMMA):
                         break # Exit shape dimension loop
            self.consume(TokenType.RBRACKET, "Expected ']' after tensor shape.")
            return TensorType(element_type, shape, start_token.line, start_token.column)
        elif self.match(TokenType.PROB):
            self.consume(TokenType.LBRACKET, "Expected '[' after 'prob'.")
            base_type = self.parse_type_annotation()
            # Optional: Parse distribution parameters if syntax allows
            distribution = None 
            self.consume(TokenType.RBRACKET, "Expected ']' after probabilistic type.")
            return ProbabilisticType(base_type, distribution, start_token.line, start_token.column)
        elif self.match(TokenType.GRAD):
            self.consume(TokenType.LBRACKET, "Expected '[' after 'grad'.")
            base_type = self.parse_type_annotation()
            self.consume(TokenType.RBRACKET, "Expected ']' after gradient type.")
            return GradientType(base_type, start_token.line, start_token.column)
        elif self.match(TokenType.IDENTIFIER):
            # User-defined type or potentially a simple type not yet matched
            name = self.previous().value
            return SimpleType(name, start_token.line, start_token.column)
        else:
            raise self.error(start_token, "Expected type name (int, float, tensor, prob, grad, or identifier).")

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
    cls.parse_layers_block = parse_layers_block # New
    cls.parse_components_block = parse_components_block # New
    cls.parse_forward_pass = parse_forward_pass # New
    cls.parse_train_method = parse_train_method # New
    cls.parse_parameter_list = parse_parameter_list
    cls.parse_type_annotation = parse_type_annotation
    
    return cls

# Apply the extension to the Parser class
import sys
from .parser import Parser
add_statement_parsers(Parser)
