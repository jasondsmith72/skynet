# Tests for Clarity self-healing system

import unittest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from clarity.compiler.parser import ClarityLexer, ClarityParser
from clarity.runtime.diagnostic_runtime import ClarityDiagnosticRuntime
from clarity.diagnostics.error_analyzer import ErrorAnalyzer
from clarity.healing.healing_engine import HealingEngine


class TestSelfHealing(unittest.TestCase):
    """Test cases for the Clarity self-healing system."""
    
    def setUp(self):
        """Set up for all tests."""
        self.error_analyzer = ErrorAnalyzer()
        self.healing_engine = HealingEngine(self.error_analyzer)
        self.runtime = ClarityDiagnosticRuntime()
    
    def test_missing_semicolon_healing(self):
        """Test healing of missing semicolon errors."""
        # Code with a missing semicolon
        code = "let x = 10\nlet y = 20;"
        
        # Simulate the error analysis
        error_message = "SyntaxError: Missing semicolon on line 1"
        analysis = {
            "type": "syntax",
            "category": "missing_semicolon",
            "analyzed": True,
            "context": {"location": {"line": 0}},
            "match": []
        }
        
        # Try to heal the code
        result = self.healing_engine.heal_missing_semicolon(code, analysis)
        
        # Check the results
        self.assertTrue(result["success"])
        self.assertEqual(result["healed_code"], "let x = 10;\nlet y = 20;")
    
    def test_undefined_variable_healing(self):
        """Test healing of undefined variable errors."""
        # Code with an undefined variable
        code = "console.log(undefinedVar);"
        
        # Simulate the error analysis
        analysis = {
            "type": "reference",
            "category": "undefined_variable",
            "analyzed": True,
            "match": ["undefinedVar"]
        }
        
        # Try to heal the code
        result = self.healing_engine.heal_undefined_variable(code, analysis)
        
        # Check the results
        self.assertTrue(result["success"])
        self.assertEqual(result["healed_code"], "let undefinedVar = null;\nconsole.log(undefinedVar);")
    
    def test_end_to_end_healing(self):
        """Test the end-to-end healing process."""
        # This test would normally use the actual runtime to execute code
        # and capture real errors, but we'll simulate it for now
        
        # Simulate a runtime error
        error_data = {
            "message": "ReferenceError: undefinedVar is not defined",
            "type": "reference",
            "pattern": "undefined_variable",
            "code_context": "console.log(undefinedVar);"
        }
        
        # Simulate the healing attempt
        original_code = "console.log(undefinedVar);"
        expected_healed_code = "let undefinedVar = null;\nconsole.log(undefinedVar);"
        
        # In a real test, we would:  
        # 1. Execute the original code with the runtime
        # 2. Capture the actual error  
        # 3. Apply healing through the runtime  
        # 4. Verify the healed code executes without errors
        
        # Instead, we'll just verify our assumptions about the healing process
        analysis = {
            "type": "reference",
            "category": "undefined_variable",
            "analyzed": True,
            "match": ["undefinedVar"]
        }
        
        result = self.healing_engine.heal_undefined_variable(original_code, analysis)
        self.assertTrue(result["success"])
        self.assertEqual(result["healed_code"], expected_healed_code)


if __name__ == '__main__':
    unittest.main()
