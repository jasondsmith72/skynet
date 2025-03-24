"""
Learning Domains for ClarityOS

This module defines the learning domains supported by ClarityOS.
"""

import logging
from enum import Enum, auto
from typing import Dict, List, Any, Optional

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
            "good_threshold": 100,
            "warning_threshold": 500,
            "critical_threshold": 1000
        },
        "throughput": {
            "unit": "ops/second",
            "good_threshold": 1000,
            "warning_threshold": 500,
            "critical_threshold": 100
        },
        "cpu_usage": {
            "unit": "percent",
            "good_threshold": 50,
            "warning_threshold": 80,
            "critical_threshold": 95
        },
        "memory_usage": {
            "unit": "percent",
            "good_threshold": 60,
            "warning_threshold": 85,
            "critical_threshold": 95
        }
    }
    
    # Stability domain metrics
    STABILITY_METRICS = {
        "error_rate": {
            "unit": "percent",
            "good_threshold": 0.1,
            "warning_threshold": 1.0,
            "critical_threshold": 5.0
        },
        "crash_frequency": {
            "unit": "crashes/day",
            "good_threshold": 0,
            "warning_threshold": 1,
            "critical_threshold": 3
        },
        "recovery_time": {
            "unit": "seconds",
            "good_threshold": 5,
            "warning_threshold": 30,
            "critical_threshold": 60
        }
    }
    
    # Security domain metrics
    SECURITY_METRICS = {
        "threat_detections": {
            "unit": "threats/day",
            "good_threshold": 0,
            "warning_threshold": 5,
            "critical_threshold": 10
        },
        "vulnerability_count": {
            "unit": "count",
            "good_threshold": 0,
            "warning_threshold": 3,
            "critical_threshold": 5
        },
        "failed_access_attempts": {
            "unit": "attempts/day",
            "good_threshold": 3,
            "warning_threshold": 10,
            "critical_threshold": 20
        }
    }
    
    # User interaction domain metrics
    USER_INTERACTION_METRICS = {
        "satisfaction_score": {
            "unit": "score",
            "good_threshold": 4.5,
            "warning_threshold": 3.5,
            "critical_threshold": 3.0
        },
        "task_completion_rate": {
            "unit": "percent",
            "good_threshold": 95,
            "warning_threshold": 85,
            "critical_threshold": 75
        },
        "error_correction_rate": {
            "unit": "percent",
            "good_threshold": 90,
            "warning_threshold": 75,
            "critical_threshold": 60
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
        
        Returns:
            "good", "warning", or "critical"
        """
        metrics = cls.get_metrics_for_domain(domain)
        if metric_name not in metrics:
            return "unknown"
            
        thresholds = metrics[metric_name]
        
        # Handle metrics where lower is better
        if metric_name in ["response_time", "error_rate", "crash_frequency", "recovery_time", 
                           "threat_detections", "vulnerability_count", "failed_access_attempts"]:
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
    
    @classmethod
    def get_strategies_for_domain(cls, domain: LearningDomain) -> List[Dict]:
        """Get improvement strategies for a specific domain."""
        if domain == LearningDomain.PERFORMANCE:
            return [
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
                }
            ]
        elif domain == LearningDomain.STABILITY:
            return [
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
        elif domain == LearningDomain.SECURITY:
            return [
                {
                    "name": "input_validation_enhancement",
                    "description": "Enhance input validation to prevent security vulnerabilities",
                    "applicability": ["validation_failures", "injection_attempts"]
                },
                {
                    "name": "access_control_improvement",
                    "description": "Improve access control mechanisms",
                    "applicability": ["unauthorized_access_attempts", "privilege_escalation"]
                },
                {
                    "name": "encryption_enhancement",
                    "description": "Enhance data encryption for sensitive information",
                    "applicability": ["data_exposure", "privacy_concerns"]
                }
            ]
        elif domain == LearningDomain.USER_INTERACTION:
            return [
                {
                    "name": "interface_simplification",
                    "description": "Simplify user interfaces for improved usability",
                    "applicability": ["low_satisfaction_score", "low_task_completion_rate"]
                },
                {
                    "name": "error_suggestion_improvement",
                    "description": "Improve error suggestions and correction mechanisms",
                    "applicability": ["high_user_errors", "low_error_correction_rate"]
                },
                {
                    "name": "context_awareness_enhancement",
                    "description": "Enhance context awareness for better user assistance",
                    "applicability": ["context_misidentification", "irrelevant_suggestions"]
                }
            ]
        else:
            return []
    
    @classmethod
    def select_strategy(cls, domain: LearningDomain, issues: List[str]) -> Optional[Dict]:
        """Select the most appropriate improvement strategy for given issues."""
        strategies = cls.get_strategies_for_domain(domain)
        
        if not strategies or not issues:
            return None
        
        # Score strategies based on applicability to issues
        scored_strategies = []
        for strategy in strategies:
            score = sum(1 for issue in issues if issue in strategy["applicability"])
            if score > 0:
                scored_strategies.append((strategy, score))
        
        # Return the strategy with the highest score
        if scored_strategies:
            return sorted(scored_strategies, key=lambda x: x[1], reverse=True)[0][0]
        else:
            return None
