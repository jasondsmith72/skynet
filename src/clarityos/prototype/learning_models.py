"""
Learning Models for AI OS

This module defines the data models used by the Learning Agent system.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class LearningMode(Enum):
    """Different learning modes for the agent."""
    OBSERVATION = "observation"      # Passive watching and data collection
    EXPLORATION = "exploration"      # Active testing to understand behavior
    EXPERIMENTATION = "experimentation"  # Controlled tests of hypotheses
    IMPLEMENTATION = "implementation"    # Applying learned patterns to build components
    OPTIMIZATION = "optimization"    # Improving existing components


class LearningDomain(Enum):
    """Domains of knowledge that can be learned."""
    HARDWARE = "hardware"            # Hardware capabilities and interfaces
    RESOURCES = "resources"          # Resource management and allocation
    MEMORY = "memory"                # Memory models and management
    STORAGE = "storage"              # Storage patterns and file systems
    SCHEDULING = "scheduling"        # Process scheduling and management
    NETWORKING = "networking"        # Network protocols and management
    SECURITY = "security"            # Security models and protections
    USER_INTERACTION = "user_interaction"  # User interfaces and interaction patterns


@dataclass
class Hypothesis:
    """A hypothesis about system behavior to be tested."""
    id: str
    domain: LearningDomain
    description: str
    confidence: float = 0.0  # 0.0 to 1.0
    tests_run: int = 0
    successful_tests: int = 0
    created_at: float = field(default_factory=time.time)
    last_tested: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of tests."""
        return self.successful_tests / self.tests_run if self.tests_run > 0 else 0.0


@dataclass
class Observation:
    """An observation of system behavior."""
    id: str
    domain: LearningDomain
    description: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    related_hypotheses: List[str] = field(default_factory=list)


@dataclass
class Experiment:
    """An experiment to test a hypothesis."""
    id: str
    hypothesis_id: str
    description: str
    parameters: Dict[str, Any]
    expected_outcome: str
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    success: Optional[bool] = None


@dataclass
class KnowledgeItem:
    """A piece of verified knowledge about the system."""
    id: str
    domain: LearningDomain
    description: str
    confidence: float  # 0.0 to 1.0
    source_hypotheses: List[str]
    related_knowledge: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)


@dataclass
class ComponentTemplate:
    """Template for generating OS components."""
    id: str
    name: str
    domain: LearningDomain
    description: str
    requirements: List[str]  # IDs of knowledge items needed
    version: str = "0.1.0"
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)


@dataclass
class SystemComponent:
    """A system component built by the learning agent."""
    id: str
    name: str
    domain: LearningDomain
    description: str
    version: str
    code: str  # In a real system, might be a reference to actual code
    based_on: List[str]  # IDs of knowledge items used
    dependencies: List[str] = field(default_factory=list)  # IDs of other components
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metrics: Dict[str, Any] = field(default_factory=dict)
