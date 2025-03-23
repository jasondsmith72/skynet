"""
Clarity Programming Language Abstract Syntax Tree (AST)

This module defines the AST nodes for the Clarity programming language,
representing the syntactic structure of programs after parsing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, Any


@dataclass
class Node:
    """Base class for all AST nodes."""
    # Location information for error reporting
    line: int = 0
    column: int = 0
    

@dataclass
class Identifier(Node):
    """Represents an identifier (variable name, function name, etc.)."""
    name: str = ""


@dataclass
class Literal(Node):
    """Base class for literal values (int, float, string, bool)."""
    pass


@dataclass
class IntLiteral(Literal):
    """Represents an integer literal."""
    value: int = 0


@dataclass
class FloatLiteral(Literal):
    """Represents a floating-point literal."""
    value: float = 0.0


@dataclass
class StringLiteral(Literal):
    """Represents a string literal."""
    value: str = ""


@dataclass
class BoolLiteral(Literal):
    """Represents a boolean literal."""
    value: bool = False


@dataclass
class TypeAnnotation(Node):
    """Base class for type annotations."""
    pass


@dataclass
class SimpleType(TypeAnnotation):
    """Simple type like int, float, bool, string."""
    name: str = ""


@dataclass
class TensorType(TypeAnnotation):
    """Tensor type with element type and shape information."""
    element_type: TypeAnnotation = field(default_factory=lambda: SimpleType())
    shape: List[Union[int, str]] = field(default_factory=list)


@dataclass
class ProbabilisticType(TypeAnnotation):
    """Probabilistic type with underlying type."""
    base_type: TypeAnnotation = field(default_factory=lambda: SimpleType())
    distribution: Optional['Expression'] = None


@dataclass
class GradientType(TypeAnnotation):
    """Gradient-tracking type with underlying type."""
    base_type: TypeAnnotation = field(default_factory=lambda: SimpleType())


@dataclass
class Expression(Node):
    """Base class for all expressions."""
    pass


@dataclass
class BinaryOperation(Expression):
    """Binary operation (e.g., a + b, x * y)."""
    left: Expression = field(default_factory=lambda: Expression())
    operator: str = ""
    right: Expression = field(default_factory=lambda: Expression())


@dataclass
class UnaryOperation(Expression):
    """Unary operation (e.g., -x, !condition)."""
    operator: str = ""
    operand: Expression = field(default_factory=lambda: Expression())


@dataclass
class VariableReference(Expression):
    """Reference to a variable."""
    name: Identifier = field(default_factory=lambda: Identifier())


@dataclass
class FunctionCall(Expression):
    """Function or method call."""
    function: Expression = field(default_factory=lambda: Expression())
    arguments: List[Expression] = field(default_factory=list)


@dataclass
class ModelCall(Expression):
    """Model inference call (similar to function call but specific to models)."""
    model: Expression = field(default_factory=lambda: Expression())
    inputs: List[Expression] = field(default_factory=list)


@dataclass
class MemberAccess(Expression):
    """Access to an object member (e.g., object.field)."""
    object: Expression = field(default_factory=lambda: Expression())
    member: Identifier = field(default_factory=lambda: Identifier())


@dataclass
class ArrayAccess(Expression):
    """Array/tensor indexing (e.g., array[index])."""
    array: Expression = field(default_factory=lambda: Expression())
    indices: List[Expression] = field(default_factory=list)


@dataclass
class Statement(Node):
    """Base class for all statements."""
    pass


@dataclass
class ExpressionStatement(Statement):
    """Statement consisting of a single expression."""
    expression: Expression = field(default_factory=lambda: Expression())


@dataclass
class VariableDeclaration(Statement):
    """Variable declaration statement."""
    name: Identifier = field(default_factory=lambda: Identifier())
    type_annotation: Optional[TypeAnnotation] = None
    initializer: Optional[Expression] = None


@dataclass
class Assignment(Statement):
    """Assignment statement."""
    target: Expression = field(default_factory=lambda: Expression())
    value: Expression = field(default_factory=lambda: Expression())


@dataclass
class Block(Statement):
    """Block of statements."""
    statements: List[Statement] = field(default_factory=list)


@dataclass
class IfStatement(Statement):
    """If statement with optional else block."""
    condition: Expression = field(default_factory=lambda: Expression())
    then_block: Block = field(default_factory=lambda: Block())
    else_block: Optional[Block] = None


@dataclass
class WhileLoop(Statement):
    """While loop."""
    condition: Expression = field(default_factory=lambda: Expression())
    body: Block = field(default_factory=lambda: Block())


@dataclass
class ForLoop(Statement):
    """For loop."""
    initializer: Optional[Statement] = None
    condition: Optional[Expression] = None
    update: Optional[Statement] = None
    body: Block = field(default_factory=lambda: Block())


@dataclass
class ReturnStatement(Statement):
    """Return statement."""
    value: Optional[Expression] = None


@dataclass
class ImportStatement(Statement):
    """Import statement."""
    module: Identifier = field(default_factory=lambda: Identifier())
    elements: List[Identifier] = field(default_factory=list)


@dataclass
class ConcurrentBlock(Statement):
    """Concurrent execution block."""
    statements: List[Statement] = field(default_factory=list)


@dataclass
class Parameter(Node):
    """Function or model parameter."""
    name: Identifier = field(default_factory=lambda: Identifier())
    type_annotation: Optional[TypeAnnotation] = None
    default_value: Optional[Expression] = None


@dataclass
class FunctionDeclaration(Node):
    """Function declaration."""
    name: Identifier = field(default_factory=lambda: Identifier())
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[TypeAnnotation] = None
    body: Block = field(default_factory=lambda: Block())
    decorators: List[str] = field(default_factory=list)


@dataclass
class LayerDefinition(Node):
    """Neural network layer definition."""
    name: Identifier = field(default_factory=lambda: Identifier())
    layer_type: Identifier = field(default_factory=lambda: Identifier())
    arguments: List[Expression] = field(default_factory=list)


@dataclass
class ForwardPassDefinition(Node):
    """Model forward pass definition."""
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[TypeAnnotation] = None
    body: Block = field(default_factory=lambda: Block())


@dataclass
class ModelDeclaration(Node):
    """Model declaration."""
    name: Identifier = field(default_factory=lambda: Identifier())
    layers: List[LayerDefinition] = field(default_factory=list)
    components: List[LayerDefinition] = field(default_factory=list)  # For ensemble models
    forward_pass: ForwardPassDefinition = field(default_factory=lambda: ForwardPassDefinition())
    train_method: Optional[FunctionDeclaration] = None
    decorators: List[str] = field(default_factory=list)


@dataclass
class Program(Node):
    """Root node representing a complete Clarity program."""
    imports: List[ImportStatement] = field(default_factory=list)
    functions: List[FunctionDeclaration] = field(default_factory=list)
    models: List[ModelDeclaration] = field(default_factory=list)
