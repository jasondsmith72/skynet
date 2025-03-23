"""
Code Understanding System for ClarityOS

This module provides capabilities for ClarityOS to understand its own codebase,
including code parsing, static analysis, relationship mapping, and architectural
pattern recognition. It is a foundational component for the self-programming
features of ClarityOS.
"""

import ast
import os
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Union

logger = logging.getLogger(__name__)

class CodeModel:
    """Represents the structural model of a codebase."""
    
    def __init__(self):
        self.modules = {}  # name -> ModuleInfo
        self.classes = {}  # fully qualified name -> ClassInfo
        self.functions = {}  # fully qualified name -> FunctionInfo
        self.relationships = []  # list of Relationship objects
        
    def add_module(self, module_info):
        """Add a module to the code model."""
        self.modules[module_info.name] = module_info
        
    def add_class(self, class_info):
        """Add a class to the code model."""
        self.classes[class_info.fully_qualified_name] = class_info
        
    def add_function(self, function_info):
        """Add a function to the code model."""
        self.functions[function_info.fully_qualified_name] = function_info
        
    def add_relationship(self, relationship):
        """Add a relationship to the code model."""
        self.relationships.append(relationship)


class ModuleInfo:
    """Information about a Python module."""
    
    def __init__(self, name, file_path=None, doc=None):
        self.name = name
        self.file_path = file_path
        self.doc = doc
        self.classes = []  # list of ClassInfo objects
        self.functions = []  # list of FunctionInfo objects
        self.imports = []  # list of ImportInfo objects


class ClassInfo:
    """Information about a Python class."""
    
    def __init__(self, name, module_name, bases=None, doc=None):
        self.name = name
        self.module_name = module_name
        self.fully_qualified_name = f"{module_name}.{name}"
        self.bases = bases or []
        self.doc = doc
        self.methods = []  # list of FunctionInfo objects
        self.attributes = []  # list of AttributeInfo objects


class FunctionInfo:
    """Information about a Python function or method."""
    
    def __init__(self, name, module_name, class_name=None, doc=None):
        self.name = name
        self.module_name = module_name
        self.class_name = class_name
        if class_name:
            self.fully_qualified_name = f"{module_name}.{class_name}.{name}"
        else:
            self.fully_qualified_name = f"{module_name}.{name}"
        self.doc = doc
        self.parameters = []  # list of ParameterInfo objects
        self.calls = []  # list of function names that are called
        self.return_type = None


class Relationship:
    """Represents a relationship between code entities."""
    
    def __init__(self, relationship_type, source, target, details=None):
        self.relationship_type = relationship_type
        self.source = source
        self.target = target
        self.details = details or {}


class CodeAnalyzer:
    """Analyzes Python code to build a code model."""
    
    def __init__(self):
        self.code_model = CodeModel()
        
    def analyze_directory(self, directory_path, package_prefix=""):
        """
        Recursively analyze all Python files in a directory.
        
        Args:
            directory_path: The path to the directory to analyze
            package_prefix: The package prefix for modules in this directory
        """
        logger.info(f"Analyzing directory: {directory_path} with prefix: {package_prefix}")
        
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            
            if os.path.isdir(item_path):
                # Check if this is a Python package
                if os.path.isfile(os.path.join(item_path, "__init__.py")):
                    new_prefix = f"{package_prefix}.{item}" if package_prefix else item
                    self.analyze_directory(item_path, new_prefix)
            elif item.endswith(".py"):
                module_name = item[:-3]  # Remove the .py extension
                if module_name == "__init__":
                    module_name = package_prefix
                else:
                    module_name = f"{package_prefix}.{module_name}" if package_prefix else module_name
                    
                self.analyze_file(item_path, module_name)
                
        return self.code_model
        
    def analyze_file(self, file_path, module_name):
        """
        Analyze a Python file to extract its structure.
        
        Args:
            file_path: The path to the Python file
            module_name: The name of the module
        """
        logger.info(f"Analyzing file: {file_path} as module: {module_name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code, filename=file_path)
            module_doc = ast.get_docstring(tree)
            
            module_info = ModuleInfo(module_name, file_path, module_doc)
            self.code_model.add_module(module_info)
            
            # Process classes and functions
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    self._process_class(node, module_name, module_info)
                elif isinstance(node, ast.FunctionDef):
                    self._process_function(node, module_name, None, module_info)
                    
            # Process relationships
            self._process_relationships(tree, module_name)
                    
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            
    def _process_class(self, node, module_name, module_info):
        """Process a class definition in an AST."""
        class_name = node.name
        class_doc = ast.get_docstring(node)
        
        # Get base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{self._get_attribute_full_name(base)}")
        
        class_info = ClassInfo(class_name, module_name, bases, class_doc)
        self.code_model.add_class(class_info)
        module_info.classes.append(class_info)
        
        # Process class methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self._process_function(item, module_name, class_name, module_info, class_info)
                
    def _process_function(self, node, module_name, class_name, module_info, class_info=None):
        """Process a function definition in an AST."""
        function_name = node.name
        function_doc = ast.get_docstring(node)
        
        function_info = FunctionInfo(function_name, module_name, class_name, function_doc)
        self.code_model.add_function(function_info)
        
        if class_info:
            class_info.methods.append(function_info)
        else:
            module_info.functions.append(function_info)
                
        # Process function calls
        self._process_function_calls(node, function_info)
                
    def _process_function_calls(self, node, function_info):
        """Process function calls within a function body."""
        for child_node in ast.walk(node):
            if isinstance(child_node, ast.Call):
                if isinstance(child_node.func, ast.Name):
                    function_info.calls.append(child_node.func.id)
                elif isinstance(child_node.func, ast.Attribute):
                    function_info.calls.append(self._get_attribute_full_name(child_node.func))
                    
    def _process_relationships(self, tree, module_name):
        """Process relationships between code entities."""
        # Inheritance relationships
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                class_fqn = f"{module_name}.{class_name}"
                
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_name = base.id
                        # Try to resolve the base class within the same module
                        base_fqn = f"{module_name}.{base_name}"
                        if base_fqn in self.code_model.classes:
                            relationship = Relationship("inherits_from", class_fqn, base_fqn)
                            self.code_model.add_relationship(relationship)
                    elif isinstance(base, ast.Attribute):
                        base_fqn = self._get_attribute_full_name(base)
                        relationship = Relationship("inherits_from", class_fqn, base_fqn)
                        self.code_model.add_relationship(relationship)
                        
        # Function call relationships
        for func_fqn, func_info in self.code_model.functions.items():
            for call in func_info.calls:
                # Try to resolve the call
                if "." in call:
                    # Fully qualified call
                    if call in self.code_model.functions:
                        relationship = Relationship("calls", func_fqn, call)
                        self.code_model.add_relationship(relationship)
                else:
                    # Try to resolve in the same scope
                    if func_info.class_name:
                        # Method calling another method in the same class
                        potential_target = f"{func_info.module_name}.{func_info.class_name}.{call}"
                        if potential_target in self.code_model.functions:
                            relationship = Relationship("calls", func_fqn, potential_target)
                            self.code_model.add_relationship(relationship)
                    
                    # Function in the same module
                    potential_target = f"{func_info.module_name}.{call}"
                    if potential_target in self.code_model.functions:
                        relationship = Relationship("calls", func_fqn, potential_target)
                        self.code_model.add_relationship(relationship)
                    
    def _get_attribute_full_name(self, node):
        """Get the fully qualified name of an attribute access."""
        parts = []
        current = node
        
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
            
        if isinstance(current, ast.Name):
            parts.append(current.id)
            
        parts.reverse()
        return ".".join(parts)


class CodeUnderstandingSystem:
    """
    Main system for code understanding in ClarityOS.
    
    This system provides tools for analyzing, understanding, and reasoning
    about ClarityOS's own codebase, enabling self-programming capabilities.
    """
    
    def __init__(self, root_directory=None):
        """Initialize the Code Understanding System."""
        self.root_directory = root_directory or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.analyzer = CodeAnalyzer()
        self.code_model = None
        
    def initialize(self):
        """Initialize the system by analyzing the codebase."""
        logger.info(f"Initializing Code Understanding System with root directory: {self.root_directory}")
        self.code_model = self.analyzer.analyze_directory(self.root_directory)
        logger.info(f"Code analysis complete. Found {len(self.code_model.modules)} modules, "
                   f"{len(self.code_model.classes)} classes, {len(self.code_model.functions)} functions.")
        
    def get_code_model(self):
        """Get the current code model."""
        return self.code_model
        
    def find_entity(self, name):
        """Find any code entity by name."""
        results = []
        
        # Check modules
        if name in self.code_model.modules:
            results.append(("module", self.code_model.modules[name]))
            
        # Check classes
        for class_fqn, class_info in self.code_model.classes.items():
            if class_info.name == name or class_fqn == name:
                results.append(("class", class_info))
                
        # Check functions
        for func_fqn, func_info in self.code_model.functions.items():
            if func_info.name == name or func_fqn == name:
                results.append(("function", func_info))
                
        return results
