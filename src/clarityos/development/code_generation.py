"""
Code Generation System for ClarityOS

This module provides capabilities for ClarityOS to generate and modify Python code,
enabling self-programming capabilities. It works with the Code Understanding System
to maintain consistency with existing code patterns and styles.
"""

import ast
import os
import re
import logging
import textwrap
from typing import Dict, List, Optional, Set, Tuple, Any, Union

from clarityos.development.code_understanding import CodeUnderstandingSystem, ClassInfo, FunctionInfo

logger = logging.getLogger(__name__)

class CodeTemplate:
    """
    Represents a template for generating code with customizable parameters.
    """
    
    def __init__(self, template_string: str, parameters: Optional[Dict[str, str]] = None):
        """
        Initialize a code template.
        
        Args:
            template_string: The template string with parameter placeholders
            parameters: Optional initial parameter values
        """
        self.template_string = template_string
        self.parameters = parameters or {}
        
    def set_parameter(self, name: str, value: str) -> None:
        """
        Set a parameter value.
        
        Args:
            name: The parameter name
            value: The parameter value
        """
        self.parameters[name] = value
        
    def set_parameters(self, parameters: Dict[str, str]) -> None:
        """
        Set multiple parameter values.
        
        Args:
            parameters: A dictionary of parameter names and values
        """
        self.parameters.update(parameters)
        
    def render(self) -> str:
        """
        Render the template with the current parameter values.
        
        Returns:
            The rendered code string
        """
        result = self.template_string
        for name, value in self.parameters.items():
            placeholder = f"{{{{ {name} }}}}"
            result = result.replace(placeholder, value)
        
        return result


class StyleAnalyzer:
    """
    Analyzes and extracts coding style patterns from existing code.
    """
    
    def __init__(self, code_model=None):
        """
        Initialize the style analyzer.
        
        Args:
            code_model: Optional code model from the Code Understanding System
        """
        self.code_model = code_model
        self.style_patterns = {
            "indentation": 4,  # Default to 4 spaces
            "line_length": 88,  # Default to 88 characters (Black's default)
            "quote_style": "\"",  # Default to double quotes
            "docstring_style": "\"\"\"",  # Default to triple double quotes
            "import_style": "group",  # Default to grouped imports
            "class_naming": "pascal_case",  # Default to PascalCase for classes
            "function_naming": "snake_case",  # Default to snake_case for functions
            "variable_naming": "snake_case",  # Default to snake_case for variables
        }
        
        if code_model:
            self.analyze_style()
    
    def analyze_style(self) -> None:
        """
        Analyze the coding style from the code model.
        """
        if not self.code_model:
            logger.warning("No code model provided for style analysis")
            return
        
        # Analyze a sample of files to determine coding style
        sample_files = []
        for module_name, module_info in self.code_model.modules.items():
            if module_info.file_path and os.path.exists(module_info.file_path):
                sample_files.append(module_info.file_path)
                if len(sample_files) >= 10:  # Limit to 10 sample files
                    break
        
        indentation_counts = {}
        line_length_sum = 0
        line_count = 0
        single_quote_count = 0
        double_quote_count = 0
        
        for file_path in sample_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Analyze indentation
                indentation_match = re.search(r'^( +)\S', content, re.MULTILINE)
                if indentation_match:
                    indent_size = len(indentation_match.group(1))
                    indentation_counts[indent_size] = indentation_counts.get(indent_size, 0) + 1
                
                # Analyze line length
                lines = content.split('\n')
                for line in lines:
                    if line.strip() and not line.strip().startswith('#'):
                        line_length_sum += len(line)
                        line_count += 1
                
                # Analyze quote style
                single_quote_count += content.count("'")
                double_quote_count += content.count("\"")
                
                # More style analysis can be added here
                
            except Exception as e:
                logger.error(f"Error analyzing style in {file_path}: {str(e)}")
        
        # Determine indentation style
        if indentation_counts:
            most_common_indent = max(indentation_counts.items(), key=lambda x: x[1])[0]
            self.style_patterns["indentation"] = most_common_indent
        
        # Determine average line length
        if line_count > 0:
            avg_line_length = line_length_sum // line_count
            self.style_patterns["line_length"] = min(avg_line_length, 120)  # Cap at 120
        
        # Determine quote style
        if single_quote_count > double_quote_count:
            self.style_patterns["quote_style"] = "'"
            self.style_patterns["docstring_style"] = "'''"
        else:
            self.style_patterns["quote_style"] = "\""
            self.style_patterns["docstring_style"] = "\"\"\""
    
    def get_style_patterns(self) -> Dict[str, Any]:
        """
        Get the detected style patterns.
        
        Returns:
            A dictionary of style patterns
        """
        return self.style_patterns
    
    def apply_style(self, code: str) -> str:
        """
        Apply the detected style patterns to code.
        
        Args:
            code: The code to style
            
        Returns:
            The styled code
        """
        # Apply indentation
        indent_size = self.style_patterns["indentation"]
        # Normalize indentation first
        lines = code.split('\n')
        result_lines = []
        
        # Process each line
        for line in lines:
            # Skip empty lines
            if not line.strip():
                result_lines.append('')
                continue
            
            # Calculate the indentation level
            indent_level = 0
            for char in line:
                if char == ' ':
                    indent_level += 1
                elif char == '\t':
                    indent_level += 4  # Assuming a tab is 4 spaces
                else:
                    break
            
            # Normalize to spaces
            indent_level = (indent_level + 3) // 4  # Round up to nearest 4
            new_indent = ' ' * (indent_level * indent_size)
            result_lines.append(new_indent + line.lstrip())
        
        result = '\n'.join(result_lines)
        
        # Apply quote style
        quote_style = self.style_patterns["quote_style"]
        docstring_style = self.style_patterns["docstring_style"]
        
        # Replace docstrings
        if quote_style == "'":
            result = result.replace('"""', "'''")
        else:
            result = result.replace("'''", '"""')
        
        return result


class CodeGenerator:
    """
    Generates Python code based on specifications and existing code patterns.
    """
    
    def __init__(self, code_understanding_system: Optional[CodeUnderstandingSystem] = None):
        """
        Initialize the code generator.
        
        Args:
            code_understanding_system: Optional Code Understanding System for context
        """
        self.code_understanding_system = code_understanding_system
        self.style_analyzer = StyleAnalyzer(
            code_understanding_system.get_code_model() if code_understanding_system else None
        )
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, CodeTemplate]:
        """
        Load code templates.
        
        Returns:
            A dictionary of template names and CodeTemplate objects
        """
        # Class template
        class_template = CodeTemplate(textwrap.dedent("""
        {{ class_docstring }}
        class {{ class_name }}{{ class_inheritance }}:
            {{ class_body }}
        """))
        
        # Function template
        function_template = CodeTemplate(textwrap.dedent("""
        {{ function_docstring }}
        def {{ function_name }}({{ function_parameters }}):
            {{ function_body }}
        """))
        
        # Method template
        method_template = CodeTemplate(textwrap.dedent("""
        {{ method_docstring }}
        def {{ method_name }}(self{{ method_parameters }}):
            {{ method_body }}
        """))
        
        # Module template
        module_template = CodeTemplate(textwrap.dedent("""
        {{ module_docstring }}
        
        {{ imports }}
        
        {{ module_body }}
        """))
        
        return {
            "class": class_template,
            "function": function_template,
            "method": method_template,
            "module": module_template,
        }
    
    def generate_class(self, name: str, doc: str = None, bases: List[str] = None,
                      methods: List[Dict] = None, attributes: List[Dict] = None) -> str:
        """
        Generate a class definition.
        
        Args:
            name: The class name
            doc: Optional docstring
            bases: Optional list of base classes
            methods: Optional list of method specifications
            attributes: Optional list of attribute specifications
            
        Returns:
            The generated class code
        """
        # Prepare class inheritance
        if bases and len(bases) > 0:
            inheritance = "(" + ", ".join(bases) + ")"
        else:
            inheritance = ""
        
        # Prepare docstring
        docstring_style = self.style_analyzer.get_style_patterns()["docstring_style"]
        if doc:
            class_docstring = f"{docstring_style}\n{doc}\n{docstring_style}"
        else:
            class_docstring = f"{docstring_style}\nClass {name}.\n{docstring_style}"
        
        # Prepare attributes
        attributes_code = ""
        if attributes:
            for attr in attributes:
                if "default" in attr:
                    attributes_code += f"    {attr['name']} = {attr['default']}\n"
        
        # Prepare methods
        methods_code = ""
        if methods:
            for method_spec in methods:
                method_code = self.generate_method(
                    method_spec["name"],
                    method_spec.get("doc"),
                    method_spec.get("parameters", []),
                    method_spec.get("body", "pass")
                )
                # Indent method code
                indented_method = "\n".join(f"    {line}" for line in method_code.split("\n"))
                methods_code += indented_method + "\n\n"
        
        # If no attributes or methods, add a pass statement
        if not attributes_code and not methods_code:
            class_body = "    pass"
        else:
            class_body = attributes_code + methods_code
        
        # Generate the class code
        template = self.templates["class"]
        template.set_parameters({
            "class_name": name,
            "class_inheritance": inheritance,
            "class_docstring": class_docstring,
            "class_body": class_body
        })
        
        return template.render()
    
    def generate_function(self, name: str, doc: str = None, parameters: List[Dict] = None,
                         body: str = "pass", return_type: str = None) -> str:
        """
        Generate a function definition.
        
        Args:
            name: The function name
            doc: Optional docstring
            parameters: Optional list of parameter specifications
            body: Optional function body
            return_type: Optional return type annotation
            
        Returns:
            The generated function code
        """
        # Prepare docstring
        docstring_style = self.style_analyzer.get_style_patterns()["docstring_style"]
        if doc:
            function_docstring = f"{docstring_style}\n{doc}\n{docstring_style}"
        else:
            function_docstring = f"{docstring_style}\nFunction {name}.\n{docstring_style}"
        
        # Prepare parameters
        params_str = ""
        if parameters:
            param_parts = []
            for param in parameters:
                param_str = param["name"]
                if "type" in param:
                    param_str += f": {param['type']}"
                if "default" in param:
                    param_str += f" = {param['default']}"
                param_parts.append(param_str)
            params_str = ", ".join(param_parts)
        
        # Add return type if specified
        function_signature = name
        if return_type:
            function_signature += f" -> {return_type}"
        
        # Ensure body is properly indented
        body_lines = body.split("\n")
        indented_body = "\n".join(f"    {line}" if line.strip() else line for line in body_lines)
        
        # Generate the function code
        template = self.templates["function"]
        template.set_parameters({
            "function_name": function_signature,
            "function_parameters": params_str,
            "function_docstring": function_docstring,
            "function_body": indented_body
        })
        
        return template.render()
    
    def generate_method(self, name: str, doc: str = None, parameters: List[Dict] = None,
                       body: str = "pass", return_type: str = None) -> str:
        """
        Generate a method definition.
        
        Args:
            name: The method name
            doc: Optional docstring
            parameters: Optional list of parameter specifications
            body: Optional method body
            return_type: Optional return type annotation
            
        Returns:
            The generated method code
        """
        # Method generation is similar to function, but with 'self' parameter
        # Prepare docstring
        docstring_style = self.style_analyzer.get_style_patterns()["docstring_style"]
        if doc:
            method_docstring = f"{docstring_style}\n{doc}\n{docstring_style}"
        else:
            method_docstring = f"{docstring_style}\nMethod {name}.\n{docstring_style}"
        
        # Prepare parameters
        params_str = ""
        if parameters:
            param_parts = []
            for param in parameters:
                param_str = param["name"]
                if "type" in param:
                    param_str += f": {param['type']}"
                if "default" in param:
                    param_str += f" = {param['default']}"
                param_parts.append(param_str)
            params_str = ", " + ", ".join(param_parts) if param_parts else ""
        
        # Add return type if specified
        method_signature = name
        if return_type:
            method_signature += f" -> {return_type}"
        
        # Ensure body is properly indented
        indented_body = body
        
        # Generate the method code
        template = self.templates["method"]
        template.set_parameters({
            "method_name": method_signature,
            "method_parameters": params_str,
            "method_docstring": method_docstring,
            "method_body": indented_body
        })
        
        return template.render()
    
    def generate_module(self, doc: str = None, imports: List[str] = None,
                       content: str = None) -> str:
        """
        Generate a module.
        
        Args:
            doc: Optional module docstring
            imports: Optional list of import statements
            content: Optional module content
            
        Returns:
            The generated module code
        """
        # Prepare docstring
        docstring_style = self.style_analyzer.get_style_patterns()["docstring_style"]
        if doc:
            module_docstring = f"{docstring_style}\n{doc}\n{docstring_style}"
        else:
            module_docstring = f"{docstring_style}\nModule.\n{docstring_style}"
        
        # Prepare imports
        imports_str = ""
        if imports:
            imports_str = "\n".join(imports) + "\n\n"
        
        # Generate the module code
        template = self.templates["module"]
        template.set_parameters({
            "module_docstring": module_docstring,
            "imports": imports_str,
            "module_body": content or ""
        })
        
        # Apply style
        code = template.render()
        return self.style_analyzer.apply_style(code)
    
    def generate_from_spec(self, spec: Dict) -> str:
        """
        Generate code from a specification.
        
        Args:
            spec: A dictionary specifying the code to generate
            
        Returns:
            The generated code
        """
        if "type" not in spec:
            raise ValueError("Specification must include a 'type' field")
        
        if spec["type"] == "class":
            return self.generate_class(
                spec["name"],
                spec.get("doc"),
                spec.get("bases"),
                spec.get("methods"),
                spec.get("attributes")
            )
        elif spec["type"] == "function":
            return self.generate_function(
                spec["name"],
                spec.get("doc"),
                spec.get("parameters"),
                spec.get("body", "pass"),
                spec.get("return_type")
            )
        elif spec["type"] == "method":
            return self.generate_method(
                spec["name"],
                spec.get("doc"),
                spec.get("parameters"),
                spec.get("body", "pass"),
                spec.get("return_type")
            )
        elif spec["type"] == "module":
            return self.generate_module(
                spec.get("doc"),
                spec.get("imports"),
                spec.get("content")
            )
        else:
            raise ValueError(f"Unknown specification type: {spec['type']}")


class CodeGenerationSystem:
    """
    Main system for code generation in ClarityOS.
    
    This system provides tools for generating and modifying code based on
    high-level specifications and learned patterns from existing code.
    """
    
    def __init__(self, code_understanding_system: Optional[CodeUnderstandingSystem] = None):
        """
        Initialize the Code Generation System.
        
        Args:
            code_understanding_system: Optional Code Understanding System for context
        """
        self.code_understanding_system = code_understanding_system
        self.code_generator = CodeGenerator(code_understanding_system)
    
    def generate_code(self, spec: Dict) -> str:
        """
        Generate code from a specification.
        
        Args:
            spec: A dictionary specifying the code to generate
            
        Returns:
            The generated code
        """
        return self.code_generator.generate_from_spec(spec)
    
    def generate_component(self, component_name: str, component_type: str,
                          parent_component: str = None, features: List[str] = None) -> str:
        """
        Generate a component based on its name, type, and features.
        
        Args:
            component_name: The name of the component
            component_type: The type of component ("agent", "manager", "interface", etc.)
            parent_component: Optional parent component
            features: Optional list of features to include
            
        Returns:
            The generated component code
        """
        # Generate appropriate imports based on component type
        imports = [
            "import logging",
            "from typing import Dict, List, Optional, Any"
        ]
        
        if component_type == "agent":
            imports.append("from clarityos.core.agent_base import Agent")
            imports.append("from clarityos.core.message_bus import MessageBus")
            imports.append("from clarityos.core.priority import Priority")
            
            # Generate agent class
            class_spec = {
                "type": "class",
                "name": f"{component_name}Agent",
                "bases": ["Agent"],
                "doc": f"{component_name} agent for ClarityOS.\n\nThis agent is responsible for {component_name.lower()} operations.",
                "methods": [
                    {
                        "name": "__init__",
                        "doc": "Initialize the agent.",
                        "parameters": [
                            {"name": "message_bus", "type": "MessageBus"},
                            {"name": "config", "type": "Optional[Dict]", "default": "None"}
                        ],
                        "body": "super().__init__(f\"{component_name.lower()}_agent\", message_bus, config)\n\nlogger = logging.getLogger(__name__)\nlogger.info(f\"{component_name} Agent initialized\")"
                    },
                    {
                        "name": "start",
                        "doc": "Start the agent.",
                        "return_type": "None",
                        "body": "await super().start()\n\nlogger.info(f\"{component_name} Agent started\")\n\n# Publish agent status\nawait self.message_bus.publish(\n    \"system/agents/status\",\n    {\n        \"agent\": f\"{component_name.lower()}_agent\",\n        \"status\": \"running\",\n        \"capabilities\": []\n    },\n    priority=Priority.STANDARD\n)"
                    },
                    {
                        "name": "stop",
                        "doc": "Stop the agent.",
                        "return_type": "None",
                        "body": "logger.info(f\"Stopping {component_name} Agent\")\n\nawait super().stop()\n\nlogger.info(f\"{component_name} Agent stopped\")"
                    },
                    {
                        "name": "_register_message_handlers",
                        "doc": "Register message handlers for the agent.",
                        "return_type": "None",
                        "body": "# Add message handlers here\npass"
                    }
                ]
            }
            
            # Add feature-specific methods if specified
            if features:
                for feature in features:
                    method_spec = {
                        "name": f"handle_{feature.lower().replace(' ', '_')}",
                        "doc": f"Handle {feature.lower()} operations.",
                        "parameters": [
                            {"name": "message", "type": "Dict"}
                        ],
                        "return_type": "None",
                        "body": f"# Implementation for {feature}\nlogger.info(f\"Handling {feature}\")\n\n# Respond with success\nawait self.message_bus.respond(\n    message,\n    {{\n        \"success\": True,\n        \"message\": f\"{feature} handled successfully\"\n    }},\n    priority=Priority.STANDARD\n)"
                    }
                    class_spec["methods"].append(method_spec)
            
            # Generate the module content
            content = self.code_generator.generate_class(
                class_spec["name"],
                class_spec["doc"],
                class_spec["bases"],
                class_spec["methods"]
            )
            
            # Generate the complete module
            module_spec = {
                "type": "module",
                "doc": f"{component_name} Agent for ClarityOS\n\nThis module implements the {component_name} agent responsible for {component_name.lower()} operations.",
                "imports": imports,
                "content": content
            }
            
            return self.code_generator.generate_from_spec(module_spec)
            
        elif component_type == "manager":
            # Similar implementation for manager components
            imports.append("from clarityos.core.message_bus import MessageBus")
            
            # Generate manager class
            class_spec = {
                "type": "class",
                "name": f"{component_name}Manager",
                "doc": f"{component_name} manager for ClarityOS.\n\nThis manager is responsible for {component_name.lower()} operations.",
                "methods": [
                    {
                        "name": "__init__",
                        "doc": "Initialize the manager.",
                        "parameters": [
                            {"name": "message_bus", "type": "MessageBus"},
                            {"name": "config", "type": "Optional[Dict]", "default": "None"}
                        ],
                        "body": "self.message_bus = message_bus\nself.config = config or {}\n\nself.logger = logging.getLogger(__name__)\nself.logger.info(f\"{component_name} Manager initialized\")"
                    }
                ]
            }
            
            # Add feature-specific methods if specified
            if features:
                for feature in features:
                    method_spec = {
                        "name": f"manage_{feature.lower().replace(' ', '_')}",
                        "doc": f"Manage {feature.lower()} operations.",
                        "parameters": [
                            {"name": "params", "type": "Dict"}
                        ],
                        "return_type": "Dict",
                        "body": f"# Implementation for {feature}\nself.logger.info(f\"Managing {feature}\")\n\n# Return success response\nreturn {{\n    \"success\": True,\n    \"message\": f\"{feature} managed successfully\"\n}}"
                    }
                    class_spec["methods"].append(method_spec)
            
            # Generate the module content
            content = self.code_generator.generate_class(
                class_spec["name"],
                class_spec["doc"],
                None,
                class_spec["methods"]
            )
            
            # Generate the complete module
            module_spec = {
                "type": "module",
                "doc": f"{component_name} Manager for ClarityOS\n\nThis module implements the {component_name} manager responsible for {component_name.lower()} operations.",
                "imports": imports,
                "content": content
            }
            
            return self.code_generator.generate_from_spec(module_spec)
            
        else:
            # Generic component generation for other types
            class_spec = {
                "type": "class",
                "name": f"{component_name}{component_type.capitalize()}",
                "doc": f"{component_name} {component_type} for ClarityOS.\n\nThis {component_type} is responsible for {component_name.lower()} operations.",
                "methods": [
                    {
                        "name": "__init__",
                        "doc": "Initialize the component.",
                        "parameters": [
                            {"name": "config", "type": "Optional[Dict]", "default": "None"}
                        ],
                        "body": "self.config = config or {}\n\nself.logger = logging.getLogger(__name__)\nself.logger.info(f\"{component_name} {component_type.capitalize()} initialized\")"
                    }
                ]
            }
            
            # Generate the module content
            content = self.code_generator.generate_class(
                class_spec["name"],
                class_spec["doc"],
                None,
                class_spec["methods"]
            )
            
            # Generate the complete module
            module_spec = {
                "type": "module",
                "doc": f"{component_name} {component_type.capitalize()} for ClarityOS\n\nThis module implements the {component_name} {component_type} responsible for {component_name.lower()} operations.",
                "imports": imports,
                "content": content
            }
            
            return self.code_generator.generate_from_spec(module_spec)
    
    def modify_code(self, original_code: str, modifications: Dict) -> str:
        """
        Modify existing code based on a modification specification.
        
        Args:
            original_code: The original code to modify
            modifications: A dictionary specifying the modifications to make
            
        Returns:
            The modified code
        """
        # Parse the original code to an AST
        try:
            tree = ast.parse(original_code)
        except SyntaxError as e:
            logger.error(f"Syntax error in original code: {str(e)}")
            return original_code
        
        # TODO: Implement code modification based on AST transformation
        # This is a placeholder for future implementation
        
        return original_code  # Return unmodified code for now
