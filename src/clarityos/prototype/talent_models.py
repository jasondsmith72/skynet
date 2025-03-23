"""
AI Talent Integration Models

This module defines the data models used in the AI Talent Integration Framework.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable


class TalentDomain(Enum):
    """Domains in which an AI can have specialized talents."""
    CODE_GENERATION = "code_generation"
    NATURAL_LANGUAGE = "natural_language"
    VISION = "vision"
    SECURITY = "security"
    OPTIMIZATION = "optimization"
    PLANNING = "planning"
    CREATIVITY = "creativity"
    DATA_ANALYSIS = "data_analysis"
    REASONING = "reasoning"
    UI_DESIGN = "ui_design"
    HARDWARE = "hardware"
    NETWORKING = "networking"


class TalentLevel(Enum):
    """Proficiency levels for an AI talent."""
    NOVICE = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4
    SPECIALIST = 5


class IntegrationStatus(Enum):
    """Status of an AI talent's integration with the system."""
    DISCOVERED = "discovered"
    EVALUATING = "evaluating"
    INTEGRATED = "integrated"
    LEARNING = "learning"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


@dataclass
class TalentCapability:
    """A specific capability offered by a talented AI."""
    id: str
    name: str
    description: str
    domain: TalentDomain
    level: TalentLevel
    parameters: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AITalent:
    """Represents a specialized AI with particular talents."""
    id: str
    name: str
    version: str
    description: str
    provider: str
    interface_type: str  # 'local', 'api', 'plugin', etc.
    capabilities: Dict[str, TalentCapability] = field(default_factory=dict)
    status: IntegrationStatus = IntegrationStatus.DISCOVERED
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    security_permissions: List[str] = field(default_factory=list)
    performance_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used: Optional[float] = None
    usage_count: int = 0


@dataclass
class TalentRequest:
    """A request to use a specific AI talent."""
    id: str
    talent_id: str
    capability_id: str
    parameters: Dict[str, Any]
    context: Dict[str, Any]
    priority: int = 1
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    success: Optional[bool] = None
    error: Optional[str] = None


@dataclass
class TalentEvaluation:
    """Evaluation results for a talent capability."""
    talent_id: str
    capability_id: str
    benchmark_id: str
    benchmark_name: str
    metrics: Dict[str, float]
    examples: List[Dict[str, Any]]
    problems: List[str] = field(default_factory=list)
    completed_at: float = field(default_factory=time.time)


@dataclass
class TalentLearningSession:
    """A session where the core AI learns from a specialized talent."""
    id: str
    talent_id: str
    capability_id: str
    start_time: float
    end_time: Optional[float] = None
    knowledge_before: Dict[str, Any] = field(default_factory=dict)
    knowledge_after: Dict[str, Any] = field(default_factory=dict)
    learning_examples: List[Dict[str, Any]] = field(default_factory=list)
    improvement_metrics: Dict[str, float] = field(default_factory=dict)
    status: str = "active"  # active, completed, failed


@dataclass
class KnowledgeTransfer:
    """Knowledge transferred from a specialized AI to the core OS AI."""
    id: str
    source_talent_id: str
    source_capability_id: str
    domain: TalentDomain
    description: str
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.0


@dataclass
class TalentOrchestrationTask:
    """A task that requires coordination of multiple AI talents."""
    id: str
    name: str
    description: str
    subtasks: List[Dict[str, Any]]
    assigned_talents: Dict[str, str]  # subtask_id -> talent_id
    dependencies: Dict[str, List[str]]  # subtask_id -> list of prerequisite subtask_ids
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    results: Dict[str, Any] = field(default_factory=dict)


class TalentBenchmark:
    """A benchmark for evaluating AI talent capabilities."""
    
    def __init__(self, benchmark_id: str, name: str, domain: TalentDomain, description: str):
        self.id = benchmark_id
        self.name = name
        self.domain = domain
        self.description = description
        self.test_cases: List[Dict[str, Any]] = []
        self.reference_metrics: Dict[str, float] = {}
    
    def add_test_case(self, input_data: Any, expected_output: Any, difficulty: float = 1.0):
        """Add a test case to the benchmark."""
        self.test_cases.append({
            "input": input_data,
            "expected_output": expected_output,
            "difficulty": difficulty
        })
    
    def set_reference_metrics(self, metrics: Dict[str, float]):
        """Set reference metrics for the benchmark."""
        self.reference_metrics = metrics
    
    async def evaluate(self, talent_id: str, capability_id: str, execute_func: Callable) -> TalentEvaluation:
        """Evaluate a talent capability against this benchmark."""
        # In a real implementation, would run actual test cases
        # For the prototype, return simulated results
        
        # Simulate random performance metrics
        metrics = {
            "accuracy": random.uniform(0.7, 1.0),
            "speed": random.uniform(0.5, 1.0),
            "resource_efficiency": random.uniform(0.6, 0.9),
            "reliability": random.uniform(0.8, 1.0)
        }
        
        return TalentEvaluation(
            talent_id=talent_id,
            capability_id=capability_id,
            benchmark_id=self.id,
            benchmark_name=self.name,
            metrics=metrics,
            examples=[]
        )


# Default benchmark definitions
def create_default_benchmarks() -> Dict[str, TalentBenchmark]:
    """Create a set of default benchmarks for talent evaluation."""
    import random
    
    benchmarks = {}
    
    # Code Generation Benchmark
    code_benchmark = TalentBenchmark(
        "code_gen_bench_001",
        "System Code Generation Benchmark",
        TalentDomain.CODE_GENERATION,
        "Evaluates ability to generate system-level code"
    )
    
    code_benchmark.add_test_case(
        "Write a memory allocation function that prevents fragmentation",
        "Expected: Efficient memory allocation with defragmentation logic",
        difficulty=3.0
    )
    
    code_benchmark.set_reference_metrics({
        "accuracy": 0.9,
        "speed": 0.8,
        "resource_efficiency": 0.85,
        "reliability": 0.95
    })
    
    benchmarks[code_benchmark.id] = code_benchmark
    
    # Security Benchmark
    security_benchmark = TalentBenchmark(
        "security_bench_001",
        "System Security Analysis Benchmark",
        TalentDomain.SECURITY,
        "Evaluates ability to detect and address security vulnerabilities"
    )
    
    security_benchmark.add_test_case(
        "Find vulnerabilities in a sample system architecture",
        "Expected: Identification of access control and encryption weaknesses",
        difficulty=4.0
    )
    
    security_benchmark.set_reference_metrics({
        "accuracy": 0.95,
        "speed": 0.7,
        "resource_efficiency": 0.8,
        "reliability": 0.9
    })
    
    benchmarks[security_benchmark.id] = security_benchmark
    
    # UI Design Benchmark
    ui_benchmark = TalentBenchmark(
        "ui_design_bench_001",
        "User Interface Design Benchmark",
        TalentDomain.UI_DESIGN,
        "Evaluates ability to create effective and accessible user interfaces"
    )
    
    ui_benchmark.add_test_case(
        "Design a system settings interface for both novice and expert users",
        "Expected: Intuitive, accessible design with progressive disclosure",
        difficulty=3.5
    )
    
    ui_benchmark.set_reference_metrics({
        "accuracy": 0.85,
        "speed": 0.9,
        "resource_efficiency": 0.8,
        "reliability": 0.85
    })
    
    benchmarks[ui_benchmark.id] = ui_benchmark
    
    return benchmarks
