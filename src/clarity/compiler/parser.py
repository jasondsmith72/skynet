(LiteralExpression(value=self.previous().value, type="Boolean"))
        elif self.match(TokenType.NULL):
            return Expression(LiteralExpression(value=None, type="Null"))
        else:
            # Simplified: just return a dummy expression
            return Expression(IdentifierExpression(name="dummy"))
    
    def identifier_expression(self) -> Expression:
        """Parse an identifier expression, which could be a variable, function call, etc."""
        name = self.previous().value
        
        # Check if it's a function call
        if self.match(TokenType.LEFT_PAREN):
            # Parse arguments
            arguments = []
            
            if not self.check(TokenType.RIGHT_PAREN):
                # Parse first argument
                arguments.append(self.expression())
                
                # Parse additional arguments
                while self.match(TokenType.COMMA):
                    arguments.append(self.expression())
            
            self.consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments")
            
            return Expression(CallExpression(
                callee=IdentifierExpression(name=name),
                arguments=arguments
            ))
        else:
            # It's a simple identifier
            return Expression(IdentifierExpression(name=name))
    
    def ai_expression(self) -> Expression:
        """Parse an AI expression (using ai {...})."""
        # Check for 'ai' keyword
        self.consume(TokenType.KEYWORD, "Expected 'ai' after 'using'")
        
        # Parse AI parameters
        self.consume(TokenType.LEFT_BRACE, "Expected '{' after 'ai'")
        
        properties = {}
        
        while not self.check(TokenType.RIGHT_BRACE) and not self.is_at_end():
            if self.match(TokenType.IDENTIFIER):
                # Parse property name
                name = self.previous().value
                
                self.consume(TokenType.COLON, "Expected ':' after property name")
                
                # Parse property value
                value = self.expression()
                
                properties[name] = value
            else:
                # Skip invalid property
                self.advance()
        
        self.consume(TokenType.RIGHT_BRACE, "Expected '}' after AI parameters")
        
        return Expression(AIExpression(
            kind="using ai",
            properties=properties
        ))
    
    # Helper methods for token handling
    
    def match(self, *types: TokenType) -> bool:
        """Check if the current token matches any of the given types.
        
        If it matches, consume the token and return True.
        Otherwise, leave it alone and return False.
        """
        for type in types:
            if self.check(type):
                self.advance()
                return True
        
        return False
    
    def check(self, type: TokenType) -> bool:
        """Check if the current token is of the given type."""
        if self.is_at_end():
            return False
        return self.peek().type == type
    
    def advance(self) -> Token:
        """Consume the current token and return it."""
        if not self.is_at_end():
            self.current += 1
        return self.previous()
    
    def is_at_end(self) -> bool:
        """Check if we've reached the end of the token stream."""
        return self.peek().type == TokenType.EOF
    
    def peek(self) -> Token:
        """Return the current token without consuming it."""
        return self.tokens[self.current]
    
    def previous(self) -> Token:
        """Return the most recently consumed token."""
        return self.tokens[self.current - 1]
    
    def consume(self, type: TokenType, message: str) -> Token:
        """Consume the current token if it matches the given type.
        
        If it doesn't match, throw a parse error.
        """
        if self.check(type):
            return self.advance()
        
        raise ParseError(f"{message} at {self.peek()}")
    
    def synchronize(self):
        """Skip tokens until we reach a statement boundary.
        
        Used for error recovery after a parse error.
        """
        self.advance()
        
        while not self.is_at_end():
            if self.previous().type == TokenType.SEMICOLON:
                return
            
            if self.peek().type == TokenType.KEYWORD and self.peek().value in [
                "function", "class", "if", "while", "for", "return"
            ]:
                return
            
            self.advance()