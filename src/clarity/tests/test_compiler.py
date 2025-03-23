"""
Unit tests for the Clarity compiler components.

This module contains tests for the lexer, parser, and semantic analyzer.
"""

import unittest
from clarity.compiler.lexer import tokenize, TokenType
from clarity.compiler.parser import parse
from clarity.compiler.semantic_analyzer import SemanticAnalyzer


class TestLexer(unittest.TestCase):
    """Tests for the Clarity lexer."""
    
    def test_empty_input(self):
        """Test lexer on empty input."""
        tokens = tokenize("")
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, TokenType.EOF)
    
    def test_simple_identifier(self):
        """Test lexer on simple identifier."""
        tokens = tokenize("myVar")
        self.assertEqual(len(tokens), 2)  # identifier + EOF
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "myVar")
    
    def test_keywords(self):
        """Test lexer on keywords."""
        code = "model func var if else for while return import"
        tokens = tokenize(code)
        
        # Check each token is recognized as the correct keyword
        self.assertEqual(tokens[0].type, TokenType.MODEL)
        self.assertEqual(tokens[1].type, TokenType.FUNC)
        self.assertEqual(tokens[2].type, TokenType.VAR)
        self.assertEqual(tokens[3].type, TokenType.IF)
        self.assertEqual(tokens[4].type, TokenType.ELSE)
        self.assertEqual(tokens[5].type, TokenType.FOR)
        self.assertEqual(tokens[6].type, TokenType.WHILE)
        self.assertEqual(tokens[7].type, TokenType.RETURN)
        self.assertEqual(tokens[8].type, TokenType.IMPORT)
    
    def test_ai_keywords(self):
        """Test lexer on AI-specific keywords."""
        code = "train inference layers forward backward components"
        tokens = tokenize(code)
        
        self.assertEqual(tokens[0].type, TokenType.TRAIN)
        self.assertEqual(tokens[1].type, TokenType.INFERENCE)
        self.assertEqual(tokens[2].type, TokenType.LAYERS)
        self.assertEqual(tokens[3].type, TokenType.FORWARD)
        self.assertEqual(tokens[4].type, TokenType.BACKWARD)
        self.assertEqual(tokens[5].type, TokenType.COMPONENTS)
    
    def test_literals(self):
        """Test lexer on literals."""
        code = '123 45.67 "hello" true false'
        tokens = tokenize(code)
        
        self.assertEqual(tokens[0].type, TokenType.INT)
        self.assertEqual(tokens[0].value, "123")
        
        self.assertEqual(tokens[1].type, TokenType.FLOAT)
        self.assertEqual(tokens[1].value, "45.67")
        
        self.assertEqual(tokens[2].type, TokenType.STRING)
        self.assertEqual(tokens[2].value, '"hello"')
        
        self.assertEqual(tokens[3].type, TokenType.BOOL)
        self.assertEqual(tokens[3].value, "true")
        
        self.assertEqual(tokens[4].type, TokenType.BOOL)
        self.assertEqual(tokens[4].value, "false")
    
    def test_operators(self):
        """Test lexer on operators."""
        code = "+ - * / = == != < > <= >= && || !"
        tokens = tokenize(code)
        
        self.assertEqual(tokens[0].type, TokenType.PLUS)
        self.assertEqual(tokens[1].type, TokenType.MINUS)
        self.assertEqual(tokens[2].type, TokenType.MULTIPLY)
        self.assertEqual(tokens[3].type, TokenType.DIVIDE)
        self.assertEqual(tokens[4].type, TokenType.ASSIGN)
        self.assertEqual(tokens[5].type, TokenType.EQ)
        self.assertEqual(tokens[6].type, TokenType.NEQ)
        self.assertEqual(tokens[7].type, TokenType.LT)
        self.assertEqual(tokens[8].type, TokenType.GT)
        self.assertEqual(tokens[9].type, TokenType.LTE)
        self.assertEqual(tokens[10].type, TokenType.GTE)
        self.assertEqual(tokens[11].type, TokenType.AND)
        self.assertEqual(tokens[12].type, TokenType.OR)
        self.assertEqual(tokens[13].type, TokenType.NOT)
    
    def test_delimiters(self):
        """Test lexer on delimiters."""
        code = "( ) { } [ ] , . : ; ->"
        tokens = tokenize(code)
        
        self.assertEqual(tokens[0].type, TokenType.LPAREN)
        self.assertEqual(tokens[1].type, TokenType.RPAREN)
        self.assertEqual(tokens[2].type, TokenType.LBRACE)
        self.assertEqual(tokens[3].type, TokenType.RBRACE)
        self.assertEqual(tokens[4].type, TokenType.LBRACKET)
        self.assertEqual(tokens[5].type, TokenType.RBRACKET)
        self.assertEqual(tokens[6].type, TokenType.COMMA)
        self.assertEqual(tokens[7].type, TokenType.DOT)
        self.assertEqual(tokens[8].type, TokenType.COLON)
        self.assertEqual(tokens[9].type, TokenType.SEMICOLON)
        self.assertEqual(tokens[10].type, TokenType.ARROW)
    
    def test_comments(self):
        """Test lexer on comments."""
        code = "// This is a comment\nvar x = 5;"
        tokens = tokenize(code)
        
        self.assertEqual(tokens[0].type, TokenType.COMMENT)
        self.assertEqual(tokens[1].type, TokenType.VAR)
    
    def test_decorators(self):
        """Test lexer on decorators."""
        code = "@target @dynamic_target"
        tokens = tokenize(code)
        
        self.assertEqual(tokens[0].type, TokenType.DECORATOR)
        self.assertEqual(tokens[0].value, "@target")
        self.assertEqual(tokens[1].type, TokenType.DECORATOR)
        self.assertEqual(tokens[1].value, "@dynamic_target")
    
    def test_tensor_type(self):
        """Test lexer on tensor type syntax."""
        code = "tensor<float32[3, 224, 224]>"
        tokens = tokenize(code)
        
        self.assertEqual(tokens[0].type, TokenType.TENSOR)
        self.assertEqual(tokens[1].type, TokenType.LT)
        self.assertEqual(tokens[2].type, TokenType.TYPE_FLOAT)
        self.assertEqual(tokens[3].type, TokenType.LBRACKET)
        self.assertEqual(tokens[4].type, TokenType.INT)
        self.assertEqual(tokens[5].type, TokenType.COMMA)
        self.assertEqual(tokens[6].type, TokenType.INT)
        self.assertEqual(tokens[7].type, TokenType.COMMA)
        self.assertEqual(tokens[8].type, TokenType.INT)
        self.assertEqual(tokens[9].type, TokenType.RBRACKET)
        self.assertEqual(tokens[10].type, TokenType.GT)


class TestParser(unittest.TestCase):
    """Tests for the Clarity parser."""
    
    def test_simple_function(self):
        """Test parser on simple function."""
        code = """
        func add(a: int, b: int) -> int {
            return a + b;
        }
        """
        
        ast = parse(code)
        self.assertEqual(len(ast.functions), 1)
        
        func = ast.functions[0]
        self.assertEqual(func.name.name, "add")
        self.assertEqual(len(func.parameters), 2)
        self.assertEqual(func.parameters[0].name.name, "a")
        self.assertEqual(func.parameters[1].name.name, "b")
    
    def test_simple_model(self):
        """Test parser on simple model."""
        code = """
        model TestModel {
            layers {
                layer1 = Conv2D(3, 32, kernelSize: 3);
            }
            
            forward(input: tensor<float32[3, 224, 224]>) -> tensor<float32[32, 222, 222]> {
                return layer1(input);
            }
        }
        """
        
        ast = parse(code)
        self.assertEqual(len(ast.models), 1)
        
        model = ast.models[0]
        self.assertEqual(model.name.name, "TestModel")
        self.assertEqual(len(model.layers), 1)
        self.assertEqual(model.layers[0].name.name, "layer1")
        self.assertEqual(model.forward_pass.parameters[0].name.name, "input")


class TestSemanticAnalyzer(unittest.TestCase):
    """Tests for the Clarity semantic analyzer."""
    
    def test_undefined_variable(self):
        """Test semantic analyzer detects undefined variable."""
        code = """
        func test() {
            var y = x + 1;
        }
        """
        
        ast = parse(code)
        analyzer = SemanticAnalyzer()
        errors = analyzer.analyze(ast)
        
        # We should find at least one error (undefined variable)
        self.assertGreaterEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
