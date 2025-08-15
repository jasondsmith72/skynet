"""
Clarity Programming Language Semantic Analyzer

This module implements semantic analysis for the Clarity programming language,
checking for type errors, undefined variables, and other semantic issues.
"""

from typing import Dict, Set, List, Optional, Any, Tuple
from .ast import *
from dataclasses import dataclass


class SemanticError(Exception):
    """Exception raised for semantic errors."""
    
    def __init__(self, node: Node, message: str):
        self.node = node
        self.message = message
        self.line = node.line
        self.column = node.column
        super().__init__(f"Semantic error at line {node.line}, column {node.column}: {message}")


@dataclass
class Symbol:
    """Symbol table entry for a variable, function, or model."""
    name: str
    type: Any  # Could be TypeAnnotation or more complex type
    kind: str  # "variable", "function", "model", etc.
    mutable: bool = True
    initialized: bool = True
    node: Optional[Node] = None


class SymbolTable:
    """Symbol table for tracking variables, functions, and models."""
    
    def __init__(self, parent=None):
        """
        Initialize a symbol table.
        
        Args:
            parent: Parent symbol table for outer scopes
        """
        self.symbols: Dict[str, Symbol] = {}
        self.parent = parent
    
    def define(self, symbol: Symbol) -> None:
        """Define a new symbol in the current scope."""
        self.symbols[symbol.name] = symbol
    
    def resolve(self, name: str) -> Optional[Symbol]:
        """
        Resolve a symbol by name, checking current and parent scopes.
        
        Args:
            name: Symbol name to resolve
            
        Returns:
            Symbol object if found, otherwise None
        """
        if name in self.symbols:
            return self.symbols[name]
        elif self.parent:
            return self.parent.resolve(name)
        else:
            return None
    
    def create_child_scope(self) -> 'SymbolTable':
        """Create a new symbol table with this one as the parent."""
        return SymbolTable(self)


class SemanticAnalyzer:
    """
    Semantic analyzer for the Clarity programming language.
    
    This class performs semantic analysis on the AST, checking for type errors,
    undefined variables, and other semantic issues.
    """
    
    def __init__(self):
        """Initialize the semantic analyzer."""
        # Global scope symbol table
        self.current_scope = SymbolTable()
        
        # Track current function/model for return type checking
        self.current_function = None
        self.current_model = None
        
        # Track errors
        self.errors: List[SemanticError] = []
    
    def analyze(self, program: Program) -> List[SemanticError]:
        """
        Analyze a Clarity program for semantic errors.
        
        Args:
            program: The AST of the program to analyze
            
        Returns:
            List of semantic errors found
        """
        try:
            # Clear previous analysis state
            self.current_scope = SymbolTable()
            self.errors = []
            
            # Define built-in types
            self._define_built_ins()
            
            # First pass: collect all top-level declarations
            self._declare_imports(program.imports)
            self._declare_functions(program.functions)
            self._declare_models(program.models)
            
            # Second pass: analyze each declaration in detail
            for imp in program.imports:
                self._analyze_import(imp)
            
            for func in program.functions:
                self._analyze_function(func)
            
            for model in program.models:
                self._analyze_model(model)
            
        except SemanticError as e:
            self.errors.append(e)
        
        return self.errors
    
    def _define_built_ins(self) -> None:
        """Define built-in types and functions."""
        # Built-in simple types
        for type_name in ["int", "float", "string", "bool"]:
            self.current_scope.define(Symbol(
                name=type_name,
                type=None,  # Types don't have types
                kind="type"
            ))
        
        # Built-in functions and modules would be defined here
    
    def _declare_imports(self, imports: List[ImportStatement]) -> None:
        """Declare imported modules and symbols."""
        for imp in imports:
            # Add the module to the symbol table
            module_name = imp.module.name
            self.current_scope.define(Symbol(
                name=module_name,
                type=None,  # We don't know the module's type yet
                kind="module",
                node=imp
            ))
            
            # If specific elements are imported, add them too
            for elem in imp.elements:
                self.current_scope.define(Symbol(
                    name=elem.name,
                    type=None,  # We don't know the element's type yet
                    kind="imported",
                    node=elem
                ))
    
    def _declare_functions(self, functions: List[FunctionDeclaration]) -> None:
        """Declare functions in the symbol table."""
        for func in functions:
            func_name = func.name.name
            
            # Check for duplicate definitions
            if self.current_scope.resolve(func_name):
                self.errors.append(SemanticError(
                    func, f"Function '{func_name}' is already defined"
                ))
            
            # Add function to symbol table
            self.current_scope.define(Symbol(
                name=func_name,
                type=func.return_type,  # Function's type is its return type
                kind="function",
                node=func
            ))
    
    def _declare_models(self, models: List[ModelDeclaration]) -> None:
        """Declare models in the symbol table."""
        for model in models:
            model_name = model.name.name
            
            # Check for duplicate definitions
            if self.current_scope.resolve(model_name):
                self.errors.append(SemanticError(
                    model, f"Model '{model_name}' is already defined"
                ))
            
            # Add model to symbol table
            self.current_scope.define(Symbol(
                name=model_name,
                type=model,  # Model's type is itself
                kind="model",
                node=model
            ))
    
    def _analyze_import(self, imp: ImportStatement) -> None:
        """Analyze an import statement."""
        # In a real implementation, this would check if the imported
        # module and elements exist
        pass
    
    def _analyze_function(self, func: FunctionDeclaration) -> None:
        """Analyze a function declaration."""
        # Set current function for return type checking
        prev_function = self.current_function
        self.current_function = func
        
        # Create a new scope for function parameters and body
        prev_scope = self.current_scope
        self.current_scope = self.current_scope.create_child_scope()
        
        try:
            # Analyze parameters
            for param in func.parameters:
                param_name = param.name.name
                
                # Check for duplicate parameters
                if self.current_scope.resolve(param_name):
                    self.errors.append(SemanticError(
                        param, f"Duplicate parameter name '{param_name}'"
                    ))
                
                # Add parameter to symbol table
                self.current_scope.define(Symbol(
                    name=param_name,
                    type=param.type_annotation,
                    kind="parameter",
                    node=param
                ))
            
            # Analyze function body
            self._analyze_block(func.body)
            
            # TODO: Check if all code paths return a value (if return type is specified)
            
        finally:
            # Restore previous scope and function
            self.current_scope = prev_scope
            self.current_function = prev_function
    
    def _analyze_model(self, model: ModelDeclaration) -> None:
        """Analyze a model declaration."""
        # Set current model for method checking
        prev_model = self.current_model
        self.current_model = model
        
        # Create a new scope for model components
        prev_scope = self.current_scope
        self.current_scope = self.current_scope.create_child_scope()
        
        try:
            # Analyze layer definitions
            for layer in model.layers:
                layer_name = layer.name.name
                
                # Check for duplicate layer names
                if self.current_scope.resolve(layer_name):
                    self.errors.append(SemanticError(
                        layer, f"Duplicate layer name '{layer_name}'"
                    ))
                
                # Add layer to symbol table
                self.current_scope.define(Symbol(
                    name=layer_name,
                    type=None,  # Would be inferred from layer type
                    kind="layer",
                    node=layer
                ))
                
                # Check layer arguments
                for arg in layer.arguments:
                    self._analyze_expression(arg)
            
            # Analyze model components (for ensemble models)
            for component in model.components:
                component_name = component.name.name
                
                # Check for duplicate component names
                if self.current_scope.resolve(component_name):
                    self.errors.append(SemanticError(
                        component, f"Duplicate component name '{component_name}'"
                    ))
                
                # Add component to symbol table
                self.current_scope.define(Symbol(
                    name=component_name,
                    type=None,  # Would be inferred from component type
                    kind="component",
                    node=component
                ))
                
                # Check component arguments
                for arg in component.arguments:
                    self._analyze_expression(arg)
            
            # Analyze forward pass
            if model.forward_pass:
                # Create a scope for the forward pass parameters
                forward_scope = self.current_scope.create_child_scope()
                prev_forward_scope = self.current_scope
                self.current_scope = forward_scope
                
                try:
                    # Analyze parameters
                    for param in model.forward_pass.parameters:
                        param_name = param.name.name
                        
                        # Check for duplicate parameters
                        if self.current_scope.resolve(param_name):
                            self.errors.append(SemanticError(
                                param, f"Duplicate parameter name '{param_name}'"
                            ))
                        
                        # Add parameter to symbol table
                        self.current_scope.define(Symbol(
                            name=param_name,
                            type=param.type_annotation,
                            kind="parameter",
                            node=param
                        ))
                    
                    # Add 'self' to the symbol table for the forward pass
                    self.current_scope.define(Symbol(
                        name="self",
                        type=model,
                        kind="self",
                        node=model
                    ))
                    
                    # Analyze forward pass body
                    self._analyze_block(model.forward_pass.body)
                    
                finally:
                    # Restore previous scope
                    self.current_scope = prev_forward_scope
            
            # Analyze train method if present
            if model.train_method:
                self._analyze_function(model.train_method)
            
        finally:
            # Restore previous scope and model
            self.current_scope = prev_scope
            self.current_model = prev_model
    
    def _analyze_block(self, block: Block) -> None:
        """Analyze a block of statements."""
        # Create a new scope for the block
        prev_scope = self.current_scope
        self.current_scope = self.current_scope.create_child_scope()
        
        try:
            # Analyze each statement in the block
            for stmt in block.statements:
                self._analyze_statement(stmt)
        finally:
            # Restore previous scope
            self.current_scope = prev_scope
    
    def _analyze_statement(self, stmt: Statement) -> None:
        """Analyze a statement."""
        # Delegate to appropriate method based on statement type
        if isinstance(stmt, ExpressionStatement):
            self._analyze_expression(stmt.expression)
        elif isinstance(stmt, VariableDeclaration):
            self._analyze_variable_declaration(stmt)
        elif isinstance(stmt, Assignment):
            self._analyze_assignment(stmt)
        elif isinstance(stmt, IfStatement):
            self._analyze_if_statement(stmt)
        elif isinstance(stmt, WhileLoop):
            self._analyze_while_loop(stmt)
        elif isinstance(stmt, ForLoop):
            self._analyze_for_loop(stmt)
        elif isinstance(stmt, ReturnStatement):
            self._analyze_return_statement(stmt)
        elif isinstance(stmt, ImportStatement):
            self._analyze_import(stmt)
        elif isinstance(stmt, ConcurrentBlock):
            self._analyze_concurrent_block(stmt)
        elif isinstance(stmt, Block):
            self._analyze_block(stmt)
        else:
            # Unknown statement type
            self.errors.append(SemanticError(
                stmt, f"Unknown statement type: {type(stmt).__name__}"
            ))
    
    def _analyze_variable_declaration(self, stmt: VariableDeclaration) -> None:
        if stmt.initializer:
            self._analyze_expression(stmt.initializer)

        var_name = stmt.name.name
        if self.current_scope.resolve(var_name):
            self.errors.append(SemanticError(
                stmt.name, f"Variable '{var_name}' is already defined in this scope."
            ))
        else:
            self.current_scope.define(Symbol(
                name=var_name,
                type=stmt.type_annotation,
                kind="variable",
                node=stmt
            ))

    def _analyze_assignment(self, stmt: Assignment) -> None:
        pass

    def _analyze_if_statement(self, stmt: IfStatement) -> None:
        pass

    def _analyze_while_loop(self, stmt: WhileLoop) -> None:
        pass

    def _analyze_for_loop(self, stmt: ForLoop) -> None:
        pass

    def _analyze_return_statement(self, stmt: ReturnStatement) -> None:
        pass

    def _analyze_concurrent_block(self, stmt: ConcurrentBlock) -> None:
        pass

    def _analyze_expression(self, expr: Expression) -> None:
        if isinstance(expr, VariableReference):
            if self.current_scope.resolve(expr.name.name) is None:
                self.errors.append(SemanticError(
                    expr.name, f"Variable '{expr.name.name}' is not defined."
                ))
        elif isinstance(expr, BinaryOperation):
            self._analyze_expression(expr.left)
            self._analyze_expression(expr.right)

    # The rest of the analyzer implementation would follow...
    # We'll continue in another file to keep this one shorter
