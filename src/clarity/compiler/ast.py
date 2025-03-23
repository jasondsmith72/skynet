#!/usr/bin/env python3
"""
Abstract Syntax Tree (AST) definitions for the Clarity language.

This module defines the node classes that make up the AST for Clarity code.
These nodes represent the hierarchical structure of Clarity programs after parsing.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field

# Base AST node class
class Node:
    """Base class for all AST nodes."""
    pass

@dataclass
class Parameter:
    """Function or method parameter."""
    name: str
    type: str
    optional: bool = False
    default_value: Optional['Expression'] = None

@dataclass
class VariantParameter:
    """Parameter for enum variant."""
    name: str
    type: str

@dataclass
class EnumVariant:
    """Enum variant definition."""
    name: str
    parameters: List[VariantParameter] = field(default_factory=list)

@dataclass
class Property:
    """Class or type property."""
    name: str
    type: str
    optional: bool = False
    default_value: Optional['Expression'] = None

@dataclass
class AgentPermissions:
    """Agent permissions definition."""
    can_read: List[str] = field(default_factory=list)
    can_write: List[str] = field(default_factory=list)
    can_call: List[str] = field(default_factory=list)

@dataclass
class AgentConstraints:
    """Agent constraints definition."""
    max_response_time: Optional[str] = None
    must_escalate_when: List[str] = field(default_factory=list)
    response_style_source: Optional[str] = None

@dataclass
class Range:
    """Range for for-range loops."""
    start: 'Expression'
    end: 'Expression'
    step: Optional['Expression'] = None

@dataclass
class CatchClause:
    """Catch clause in try-catch statement."""
    error_type: str
    binding: Optional[str] = None
    body: 'BlockStatement' = None

@dataclass
class RecoveryStrategy:
    """Recovery strategy for service error handling."""
    error_type: str
    strategies: List[Any] = field(default_factory=list)

@dataclass
class EventHandler:
    """Event handler in a service."""
    event_name: str
    parameters: List[str]
    body: 'BlockStatement' = None

@dataclass
class ScheduledTask:
    """Scheduled task in a service."""
    schedule: str
    body: 'BlockStatement' = None

# Program structure
@dataclass
class Program(Node):
    """Root node of the AST representing a complete program."""
    declarations: List[Node] = field(default_factory=list)

# Declarations
@dataclass
class FunctionDeclaration(Node):
    """Function declaration node."""
    name: str
    parameters: List[Parameter] = field(default_factory=list)
    return_type: Optional[str] = None
    body: 'BlockStatement' = None
    throws: bool = False
    throws_types: List[str] = field(default_factory=list)
    async_function: bool = False
    intent: Optional[str] = None

@dataclass
class VariableDeclaration(Node):
    """Variable declaration node."""
    kind: str  # 'let' or 'const'
    name: str
    type_annotation: Optional[str] = None
    initializer: Optional['Expression'] = None

@dataclass
class ClassDeclaration(Node):
    """Class declaration node."""
    name: str
    superclass: Optional[str] = None
    interfaces: List[str] = field(default_factory=list)
    properties: List[Property] = field(default_factory=list)
    constructor: Optional[FunctionDeclaration] = None
    methods: List[FunctionDeclaration] = field(default_factory=list)

@dataclass
class InterfaceDeclaration(Node):
    """Interface declaration node."""
    name: str
    methods: List[FunctionDeclaration] = field(default_factory=list)

@dataclass
class TypeDeclaration(Node):
    """Type declaration node."""
    name: str
    type_kind: str = "struct"  # 'struct', 'enum', etc.
    properties: List[Property] = field(default_factory=list)
    variants: List[EnumVariant] = field(default_factory=list)

@dataclass
class AgentDeclaration(Node):
    """Agent declaration node."""
    name: str
    permissions: Optional[AgentPermissions] = None
    capabilities: List[FunctionDeclaration] = field(default_factory=list)
    constraints: Optional[AgentConstraints] = None

@dataclass
class ServiceDeclaration(Node):
    """Service declaration node."""
    name: str
    config: List[Property] = field(default_factory=list)
    functions: List[FunctionDeclaration] = field(default_factory=list)
    recovery_strategies: List[RecoveryStrategy] = field(default_factory=list)
    event_handlers: List[EventHandler] = field(default_factory=list)
    scheduled_tasks: List[ScheduledTask] = field(default_factory=list)

# Statements
@dataclass
class Statement(Node):
    """Base class for all statement nodes."""
    pass

@dataclass
class BlockStatement(Statement):
    """Block of statements."""
    statements: List[Statement] = field(default_factory=list)

@dataclass
class IfStatement(Statement):
    """If statement node."""
    test: 'Expression'
    consequent: BlockStatement
    alternate: Optional[Union[BlockStatement, 'IfStatement']] = None
    is_guard: bool = False

@dataclass
class ForStatement(Statement):
    """For loop statement node."""
    kind: str  # 'for-in', 'for-range'
    variable: str
    iterable: Optional['Expression'] = None  # For 'for-in'
    range: Optional[Range] = None  # For 'for-range'
    body: BlockStatement = None

@dataclass
class WhileStatement(Statement):
    """While loop statement node."""
    test: 'Expression'
    body: BlockStatement = None

@dataclass
class SwitchStatement(Statement):
    """Switch statement node."""
    discriminant: 'Expression'
    cases: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ReturnStatement(Statement):
    """Return statement node."""
    expression: Optional['Expression'] = None

@dataclass
class ThrowStatement(Statement):
    """Throw statement node."""
    error: 'Expression'

@dataclass
class TryCatchStatement(Statement):
    """Try-catch statement node."""
    try_block: BlockStatement
    catch_clauses: List[CatchClause] = field(default_factory=list)
    finally_block: Optional[BlockStatement] = None

# Expressions
@dataclass
class Expression(Node):
    """Base class for all expression nodes."""
    expression: Any = None

@dataclass
class BinaryExpression(Expression):
    """Binary expression node."""
    operator: str
    left: Expression
    right: Expression

@dataclass
class UnaryExpression(Expression):
    """Unary expression node."""
    operator: str
    argument: Expression
    prefix: bool = True

@dataclass
class CallExpression(Expression):
    """Function call expression node."""
    callee: Union['IdentifierExpression', 'MemberExpression']
    arguments: List[Expression] = field(default_factory=list)

@dataclass
class MemberExpression(Expression):
    """Member access expression node."""
    object: Union['IdentifierExpression', 'MemberExpression', 'CallExpression']
    property: str
    computed: bool = False  # Whether property is accessed via [] notation

@dataclass
class IdentifierExpression(Expression):
    """Identifier expression node."""
    name: str

@dataclass
class LiteralExpression(Expression):
    """Literal value expression node."""
    value: Any
    type: str = ""  # The Clarity type of the literal

@dataclass
class AIExpression(Expression):
    """AI expression node for using AI integrations."""
    kind: str  # 'using ai', etc.
    properties: Dict[str, Any] = field(default_factory=dict)