"""
Learning Domains for ClarityOS

This module defines the learning domains supported by ClarityOS and provides
domain-specific learning handlers for the AI system.
"""

import logging
from enum import Enum, auto
from typing import Dict, List, Any, Callable, Optional

# Configure logging
logger = logging.getLogger(__name__)


class LearningDomain(Enum):
    """Enumeration of learning domains in ClarityOS."""
    
    # System optimization domains
    PERFORMANCE = auto()     # Performance optimization
    STABILITY = auto()       # System stability and error reduction
    RESOURCE = auto()        # Resource allocation and management
    
    # Security domains
    SECURITY = auto()        # System security and threat detection
    PRIVACY = auto()         # User privacy protection
    
    # User experience domains
    USER_INTERACTION = auto()  # User interface and experience
    INTENT = auto()            # User intent understanding
    
    # Infrastructure domains
    HARDWARE = auto()        # Hardware interaction and optimization
    NETWORK = auto()         # Network optimization
    STORAGE = auto()         # Storage optimization
    
    # Application domains
    APPLICATION = auto()     # Application behavior and optimization
    INTEGRATION = auto()     # System integration with external components
    
    # Knowledge domains
    KNOWLEDGE = auto()       # System knowledge base expansion
    REASONING = auto()       # Reasoning and decision making


class DomainMetrics:
    """
    Defines metrics and thresholds for different learning domains.
    These metrics are used to measure system performance and identify 
    areas for improvement.
    """
    
    # Performance domain metrics
    PERFORMANCE_METRICS = {
        "response_time": {
            "unit": "milliseconds",
            "good_threshold": 100,  # Below 100ms is good
            "warning_threshold": 500,  # 100-500ms is warning
            "critical_threshold": 1000  # Above 1000ms is critical
        },
        "throughput": {
            "unit": "ops/second",
            "good_threshold": 1000,  # Above 1000 ops/s is good
            "warning_threshold": 500,  # 500-1000 ops/s is warning
            "critical_threshold": 100  # Below 100 ops/s is critical
        },
        "cpu_usage": {
            "unit": "percent",
            "good_threshold": 50,  # Below 50% is good
            "warning_threshold": 80,  # 50-80% is warning
            "critical_threshold": 95  # Above 95% is critical
        },
        "memory_usage": {
            "unit": "percent",
            "good_threshold": 60,  # Below 60% is good
            "warning_threshold": 85,  # 60-85% is warning
            "critical_threshold": 95  # Above 95% is critical
        }
    }
    
    # Stability domain metrics
    STABILITY_METRICS = {
        "error_rate": {
            "unit": "percent",
            "good_threshold": 0.1,  # Below 0.1% is good
            "warning_threshold": 1.0,  # 0.1-1.0% is warning
            "critical_threshold": 5.0  # Above 5% is critical
        },
        "crash_frequency": {
            "unit": "crashes/day",
            "good_threshold": 0,  # 0 crashes is good
            "warning_threshold": 1,  # 1 crash is warning
            "critical_threshold": 3  # 3+ crashes is critical
        },
        "recovery_time": {
            "unit": "seconds",
            "good_threshold": 5,  # Below 5s is good
            "warning_threshold": 30,  # 5-30s is warning
            "critical_threshold": 60  # Above 60s is critical
        }
    }
    
    # Security domain metrics
    SECURITY_METRICS = {
        "threat_detections": {
            "unit": "threats/day",
            "good_threshold": 0,  # 0 threats is good
            "warning_threshold": 5,  # 1-5 threats is warning
            "critical_threshold": 10  # 10+ threats is critical
        },
        "vulnerability_count": {
            "unit": "count",
            "good_threshold": 0,  # 0 vulnerabilities is good
            "warning_threshold": 3,  # 1-3 vulnerabilities is warning
            "critical_threshold": 5  # 5+ vulnerabilities is critical
        }
    }
    
    # User interaction domain metrics
    USER_INTERACTION_METRICS = {
        "satisfaction_score": {
            "unit": "score",
            "good_threshold": 4.5,  # Above 4.5 is good
            "warning_threshold": 3.5,  # 3.5-4.5 is acceptable
            "critical_threshold": 3.0  # Below 3.0 is critical
        },
        "task_completion_rate": {
            "unit": "percent",
            "good_threshold": 95,  # Above 95% is good
            "warning_threshold": 85,  # 85-95% is acceptable
            "critical_threshold": 75  # Below 75% is critical
        }
    }
    
    @classmethod
    def get_metrics_for_domain(cls, domain: LearningDomain) -> Dict:
        """Get metrics for a specific domain."""
        domain_metrics = {
            LearningDomain.PERFORMANCE: cls.PERFORMANCE_METRICS,
            LearningDomain.STABILITY: cls.STABILITY_METRICS,
            LearningDomain.SECURITY: cls.SECURITY_METRICS,
            LearningDomain.USER_INTERACTION: cls.USER_INTERACTION_METRICS
        }
        
        return domain_metrics.get(domain, {})
    
    @classmethod
    def evaluate_metric(cls, domain: LearningDomain, metric_name: str, value: float) -> str:
        """
        Evaluate a metric value against thresholds.
        Returns: "good", "warning", or "critical"
        """
        metrics = cls.get_metrics_for_domain(domain)
        if metric_name not in metrics:
            return "unknown"
            
        thresholds = metrics[metric_name]
        
        # Handle metrics where lower is better
        if metric_name in ["response_time", "error_rate", "crash_frequency", "recovery_time", 
                          "threat_detections", "vulnerability_count"]:
            if value <= thresholds["good_threshold"]:
                return "good"
            elif value <= thresholds["warning_threshold"]:
                return "warning"
            else:
                return "critical"
        # Handle metrics where higher is better
        else:
            if value >= thresholds["good_threshold"]:
                return "good"
            elif value >= thresholds["warning_threshold"]:
                return "warning"
            else:
                return "critical"


class DomainImprovement:
    """
    Defines improvement strategies for different learning domains.
    """
    
    # Performance improvement strategies
    PERFORMANCE_STRATEGIES = [
        {
            "name": "resource_allocation_optimization",
            "description": "Optimize resource allocation based on usage patterns",
            "applicability": ["high_cpu_usage", "high_memory_usage"]
        },
        {
            "name": "caching_enhancement",
            "description": "Implement or enhance caching for frequently accessed data",
            "applicability": ["high_response_time", "high_disk_io"]
        },
        {
            "name": "parallel_processing",
            "description": "Implement parallel processing for CPU-intensive operations",
            "applicability": ["high_cpu_usage", "low_throughput"]
        },
        {
            "name": "algorithm_optimization",
            "description": "Optimize algorithms for better performance",
            "applicability": ["high_response_time", "high_cpu_usage"]
        }
    ]
    
    # Stability improvement strategies
    STABILITY_STRATEGIES = [
        {
            "name": "error_handling_enhancement",
            "description": "Enhance error handling and recovery mechanisms",
            "applicability": ["high_error_rate", "high_crash_frequency"]
        },
        {
            "name": "resource_leak_detection",
            "description": "Implement detection and prevention of resource leaks",
            "applicability": ["increasing_memory_usage", "degrading_performance"]
        },
        {
            "name": "component_isolation",
            "description": "Improve component isolation to prevent cascade failures",
            "applicability": ["multiple_component_failures", "high_recovery_time"]
        }
    ]
    
    # Security improvement strategies
    SECURITY_STRATEGIES = [
        {
            "name": "input_validation_enhancement",
            "description": "Enhance input validation to prevent security vulnerabilities",
            "applicability": ["validation_failures", "injection_attempts"]
        },
        {
            "name": "access_control_refinement",
            "description": "Refine access control mechanisms",
            "applicability": ["unauthorized_access_attempts", "privilege_escalation"]
        },
        {
            "name": "encryption_upgrade",
            "description": "Upgrade encryption mechanisms for sensitive data",
            "applicability": ["data_exposure", "encryption_vulnerabilities"]
        }
    ]
    
    # User interaction improvement strategies
    USER_INTERACTION_STRATEGIES = [
        {
            "name": "interface_simplification",
            "description": "Simplify interfaces for better user experience",
            "applicability": ["low_satisfaction", "high_error_rate"]
        },
        {
            "name": "intelligent_defaults",
            "description": "Implement intelligent defaults based on user behavior",
            "applicability": ["repeated_manual_configuration", "low_completion_rate"]
        },
        {
            "name": "feedback_enhancement",
            "description": "Improve system feedback for user actions",
            "applicability": ["user_confusion", "repeated_actions"]
        }
    ]
    
    @classmethod
    def get_strategies_for_domain(cls, domain: LearningDomain) -> List[Dict]:
        """Get improvement strategies for a specific domain."""
        domain_strategies = {
            LearningDomain.PERFORMANCE: cls.PERFORMANCE_STRATEGIES,
            LearningDomain.STABILITY: cls.STABILITY_STRATEGIES,
            LearningDomain.SECURITY: cls.SECURITY_STRATEGIES,
            LearningDomain.USER_INTERACTION: cls.USER_INTERACTION_STRATEGIES
        }
        
        return domain_strategies.get(domain, [])
    
    @classmethod
    def find_strategy_for_issue(cls, domain: LearningDomain, issues: List[str]) -> Optional[Dict]:
        """Find an appropriate improvement strategy for identified issues."""
        strategies = cls.get_strategies_for_domain(domain)
        
        # Find strategies that address any of the issues
        matching_strategies = []
        for strategy in strategies:
            applicability = strategy.get("applicability", [])
            if any(issue in applicability for issue in issues):
                matching_strategies.append(strategy)
        
        # Return the best matching strategy if any found
        if matching_strategies:
            return max(matching_strategies, 
                       key=lambda s: sum(1 for issue in issues if issue in s.get("applicability", [])))
        
        return None


# Domain handler functions for simple cases
async def handle_performance_learning(data: Dict) -> Dict:
    """Handle performance domain learning."""
    metrics = data.get("metrics", {})
    
    # Analyze metrics
    issues = []
    for metric_name, value in metrics.items():
        status = DomainMetrics.evaluate_metric(LearningDomain.PERFORMANCE, metric_name, value)
        if status in ["warning", "critical"]:
            if metric_name == "response_time" and value > 500:
                issues.append("high_response_time")
            elif metric_name == "cpu_usage" and value > 80:
                issues.append("high_cpu_usage")
            elif metric_name == "memory_usage" and value > 85:
                issues.append("high_memory_usage")
            elif metric_name == "throughput" and value < 500:
                issues.append("low_throughput")
    
    # Get improvement strategy
    strategy = DomainImprovement.find_strategy_for_issue(LearningDomain.PERFORMANCE, issues)
    
    return {
        "domain": "performance",
        "issues_identified": issues,
        "improvement_strategy": strategy,
        "analysis_complete": True
    }


async def handle_stability_learning(data: Dict) -> Dict:
    """Handle stability domain learning."""
    metrics = data.get("metrics", {})
    
    # Analyze metrics
    issues = []
    for metric_name, value in metrics.items():
        status = DomainMetrics.evaluate_metric(LearningDomain.STABILITY, metric_name, value)
        if status in ["warning", "critical"]:
            if metric_name == "error_rate" and value > 1.0:
                issues.append("high_error_rate")
            elif metric_name == "crash_frequency" and value > 1:
                issues.append("high_crash_frequency")
            elif metric_name == "recovery_time" and value > 30:
                issues.append("high_recovery_time")
    
    # Get improvement strategy
    strategy = DomainImprovement.find_strategy_for_issue(LearningDomain.STABILITY, issues)
    
    return {
        "domain": "stability",
        "issues_identified": issues,
        "improvement_strategy": strategy,
        "analysis_complete": True
    }


async def handle_security_learning(data: Dict) -> Dict:
    """Handle security domain learning."""
    events = data.get("events", [])
    
    # Analyze security events
    issue_counts = {}
    for event in events:
        event_type = event.get("type", "unknown")
        if event_type == "validation_failure":
            issue_counts["validation_failures"] = issue_counts.get("validation_failures", 0) + 1
        elif event_type == "injection_attempt":
            issue_counts["injection_attempts"] = issue_counts.get("injection_attempts", 0) + 1
        elif event_type == "unauthorized_access":
            issue_counts["unauthorized_access_attempts"] = issue_counts.get("unauthorized_access_attempts", 0) + 1
    
    # Get issues above threshold
    issues = [issue for issue, count in issue_counts.items() if count > 3]
    
    # Get improvement strategy
    strategy = DomainImprovement.find_strategy_for_issue(LearningDomain.SECURITY, issues)
    
    return {
        "domain": "security",
        "issues_identified": issues,
        "improvement_strategy": strategy,
        "analysis_complete": True
    }


async def handle_user_interaction_learning(data: Dict) -> Dict:
    """Handle user interaction domain learning."""
    feedback = data.get("feedback", [])
    
    # Analyze user feedback
    satisfaction_scores = [item.get("satisfaction", 0) for item in feedback if "satisfaction" in item]
    completion_rates = [item.get("completion_rate", 0) for item in feedback if "completion_rate" in item]
    
    issues = []
    if satisfaction_scores and sum(satisfaction_scores) / len(satisfaction_scores) < 3.5:
        issues.append("low_satisfaction")
    if completion_rates and sum(completion_rates) / len(completion_rates) < 85:
        issues.append("low_completion_rate")
    
    # Get improvement strategy
    strategy = DomainImprovement.find_strategy_for_issue(LearningDomain.USER_INTERACTION, issues)
    
    return {
        "domain": "user_interaction",
        "issues_identified": issues,
        "improvement_strategy": strategy,
        "analysis_complete": True
    }


def get_domain_handler(domain: LearningDomain) -> Callable:
    """Get the appropriate handler function for a learning domain."""
    handlers = {
        LearningDomain.PERFORMANCE: handle_performance_learning,
        LearningDomain.STABILITY: handle_stability_learning,
        LearningDomain.SECURITY: handle_security_learning,
        LearningDomain.USER_INTERACTION: handle_user_interaction_learning
    }
    
    return handlers.get(domain, lambda data: {"error": "Domain not supported"})
