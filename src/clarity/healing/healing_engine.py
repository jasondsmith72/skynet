# Clarity Healing Engine

class HealingEngine:
    """Engine for automatically healing errors in Clarity code."""
    
    def __init__(self, error_analyzer=None):
        self.error_analyzer = error_analyzer
        self.healing_strategies = {}
        self.applied_fixes = []
        self.healing_success_rate = {}
        self.load_healing_strategies()
    
    def load_healing_strategies(self):
        """Load healing strategies for different error types."""
        # Syntax error healers
        self.healing_strategies["syntax"] = {
            "missing_semicolon": self.heal_missing_semicolon,
            "missing_brace": self.heal_missing_brace,
            "unexpected_token": self.heal_unexpected_token
        }
        
        # Type error healers
        self.healing_strategies["type"] = {
            "type_mismatch": self.heal_type_mismatch,
            "null_reference": self.heal_null_reference
        }
        
        # Reference error healers
        self.healing_strategies["reference"] = {
            "undefined_variable": self.heal_undefined_variable,
            "undefined_function": self.heal_undefined_function
        }
        
        # Logic error healers
        self.healing_strategies["logic"] = {
            "infinite_loop": self.heal_infinite_loop,
            "off_by_one": self.heal_off_by_one
        }
    
    def heal(self, code, error, context=None, execution_trace=None):
        """Attempt to heal code based on the error and context."""
        if not self.error_analyzer:
            analysis = {
                "type": "unknown",
                "category": "unknown",
                "analyzed": False
            }
        else:
            analysis = self.error_analyzer.analyze_error(
                error, code, execution_trace
            )
        
        if not analysis["analyzed"]:
            return {
                "success": False,
                "message": "Error could not be analyzed",
                "original_code": code,
                "healed_code": None,
                "confidence": 0
            }
        
        # Get appropriate healing strategy
        error_type = analysis["type"]
        error_category = analysis["category"]
        
        type_strategies = self.healing_strategies.get(error_type, {})
        strategy = type_strategies.get(error_category)
        
        if not strategy:
            return {
                "success": False,
                "message": f"No healing strategy available for {error_type}/{error_category}",
                "original_code": code,
                "healed_code": None,
                "confidence": 0
            }
        
        # Apply the healing strategy
        try:
            healing_result = strategy(code, analysis, context)
            
            # Record the applied fix for learning
            self.applied_fixes.append({
                "error_type": error_type,
                "error_category": error_category,
                "original_code": code,
                "healed_code": healing_result["healed_code"],
                "success": healing_result["success"],
                "confidence": healing_result["confidence"]
            })
            
            # Update success rate statistics
            key = f"{error_type}/{error_category}"
            if key not in self.healing_success_rate:
                self.healing_success_rate[key] = {
                    "attempts": 0,
                    "successes": 0
                }
            
            self.healing_success_rate[key]["attempts"] += 1
            if healing_result["success"]:
                self.healing_success_rate[key]["successes"] += 1
            
            return healing_result
        except Exception as e:
            return {
                "success": False,
                "message": f"Healing failed: {str(e)}",
                "original_code": code,
                "healed_code": None,
                "confidence": 0,
                "error": str(e)
            }
    
    # Syntax error healers
    def heal_missing_semicolon(self, code, analysis, context=None):
        """Heal missing semicolon errors."""
        # This is a simplified implementation
        # In a real implementation, we would analyze the code to find where semicolons are missing
        lines = code.split('\n')
        location = analysis.get("context", {}).get("location", {"line": 0})
        line_index = location["line"]
        
        if 0 <= line_index < len(lines):
            line = lines[line_index]
            if not line.strip().endswith(';'):
                lines[line_index] = line + ';'
                
                return {
                    "success": True,
                    "message": "Added missing semicolon",
                    "original_code": code,
                    "healed_code": '\n'.join(lines),
                    "confidence": 0.9
                }
        
        return {
            "success": False,
            "message": "Could not locate missing semicolon",
            "original_code": code,
            "healed_code": None,
            "confidence": 0
        }
    
    def heal_missing_brace(self, code, analysis, context=None):
        """Heal missing brace errors."""
        # This would involve complex bracket matching and analysis
        # Simplified placeholder implementation
        return {
            "success": False,
            "message": "Missing brace healing not implemented",
            "original_code": code,
            "healed_code": None,
            "confidence": 0
        }
    
    def heal_unexpected_token(self, code, analysis, context=None):
        """Heal unexpected token errors."""
        # This would involve syntax tree analysis and correction
        # Simplified placeholder implementation
        return {
            "success": False,
            "message": "Unexpected token healing not implemented",
            "original_code": code,
            "healed_code": None,
            "confidence": 0
        }
    
    # Type error healers
    def heal_type_mismatch(self, code, analysis, context=None):
        """Heal type mismatch errors."""
        # Check if we have enough information about the error
        if not analysis.get("code_snippet"):
            return {
                "success": False,
                "message": "Insufficient context for type mismatch healing",
                "original_code": code,
                "healed_code": None,
                "confidence": 0
            }
        
        # Extract code snippet and try to identify the operation
        code_snippet = analysis.get("code_snippet", "")
        
        # Handle string to number conversion in operations
        import re
        
        # Check for operations between string and number
        # Example: "let total = price * quantity;" where price is a string
        string_number_op = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*([+\-*/])\s*([a-zA-Z_][a-zA-Z0-9_]*)', code_snippet)
        if string_number_op:
            left_var, operator, right_var = string_number_op.groups()
            
            # Determine if the error is in the code_snippet - if so, modify it directly
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if code_snippet in line:
                    # Replace the operation with appropriate type conversion
                    new_line = line.replace(
                        code_snippet,
                        f"let total = parseFloat({left_var}) {operator} {right_var};"
                    )
                    lines[i] = new_line
                    return {
                        "success": True,
                        "message": f"Added parseFloat() to convert string to number",
                        "original_code": code,
                        "healed_code": '\n'.join(lines),
                        "confidence": 0.85
                    }
        
        # Look for variable declarations with string initialization that should be numbers
        string_init = re.search(r'let\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*["\'](\d+)["\']', code)
        if string_init:
            var_name, number_value = string_init.groups()
            
            # Determine if the error is in the code
            lines = code.split('\n')
            for i, line in enumerate(lines):
                pattern = f'let {var_name} = "{number_value}"'
                pattern2 = f"let {var_name} = '{number_value}'"
                
                if pattern in line:
                    # Replace the string with a number
                    new_line = line.replace(pattern, f'let {var_name} = {number_value}')
                    lines[i] = new_line
                    return {
                        "success": True,
                        "message": f"Converted string value to number for variable {var_name}",
                        "original_code": code,
                        "healed_code": '\n'.join(lines),
                        "confidence": 0.9
                    }
                elif pattern2 in line:
                    # Handle single quotes
                    new_line = line.replace(pattern2, f'let {var_name} = {number_value}')
                    lines[i] = new_line
                    return {
                        "success": True,
                        "message": f"Converted string value to number for variable {var_name}",
                        "original_code": code,
                        "healed_code": '\n'.join(lines),
                        "confidence": 0.9
                    }
        
        return {
            "success": False,
            "message": "Could not determine how to fix type mismatch",
            "original_code": code,
            "healed_code": None,
            "confidence": 0
        }
    
    def heal_null_reference(self, code, analysis, context=None):
        """Heal null reference errors."""
        # This would involve adding null checks
        # Simplified placeholder implementation
        return {
            "success": False,
            "message": "Null reference healing not implemented",
            "original_code": code,
            "healed_code": None,
            "confidence": 0
        }
    
    # Reference error healers
    def heal_undefined_variable(self, code, analysis, context=None):
        """Heal undefined variable errors."""
        # This would involve adding variable declarations
        # Simplified placeholder implementation
        variable_name = ""
        if analysis.get("match") and len(analysis["match"]) > 0:
            variable_name = analysis["match"][0]
        
        if variable_name:
            # Add a variable declaration at the beginning of the code
            healed_code = f"let {variable_name} = null;\n{code}"
            
            return {
                "success": True,
                "message": f"Added declaration for undefined variable '{variable_name}'",
                "original_code": code,
                "healed_code": healed_code,
                "confidence": 0.7
            }
        
        return {
            "success": False,
            "message": "Could not determine undefined variable name",
            "original_code": code,
            "healed_code": None,
            "confidence": 0
        }
    
    def heal_undefined_function(self, code, analysis, context=None):
        """Heal undefined function errors."""
        # This would involve adding function stubs
        # Simplified placeholder implementation
        return {
            "success": False,
            "message": "Undefined function healing not implemented",
            "original_code": code,
            "healed_code": None,
            "confidence": 0
        }
    
    # Logic error healers
    def heal_infinite_loop(self, code, analysis, context=None):
        """Heal infinite loop errors."""
        # This would involve fixing loop conditions
        # Simplified placeholder implementation
        return {
            "success": False,
            "message": "Infinite loop healing not implemented",
            "original_code": code,
            "healed_code": None,
            "confidence": 0
        }
    
    def heal_off_by_one(self, code, analysis, context=None):
        """Heal off-by-one errors."""
        # This would involve fixing array indices and loop boundaries
        # Simplified placeholder implementation
        return {
            "success": False,
            "message": "Off-by-one error healing not implemented",
            "original_code": code,
            "healed_code": None,
            "confidence": 0
        }