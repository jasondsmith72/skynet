"""
Learning Strategies for ClarityOS

This module implements various learning strategies for the ClarityOS learning framework.
These strategies enable the system to learn and adapt based on various data sources.
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional

from src.clarityos.core.message_bus import MessageBus
from src.clarityos.learning.domains import LearningDomain

# Configure logging
logger = logging.getLogger(__name__)


class LearningStrategy:
    """Base class for all learning strategies."""
    
    def __init__(self, domain: LearningDomain, message_bus: MessageBus, config: Optional[Dict] = None):
        """Initialize the learning strategy."""
        self.domain = domain
        self.message_bus = message_bus
        self.config = config or {}
        self.data_storage = []
        self.learning_results = {}
        self.last_learning_cycle = None
        
        # Data storage limits
        self.max_data_points = self.config.get("max_data_points", 1000)
        self.data_retention_days = self.config.get("data_retention_days", 30)
        
        # Configure metrics
        self.metrics = {
            "data_points_processed": 0,
            "learning_cycles_completed": 0,
            "improvements_generated": 0,
            "last_cycle_duration": 0
        }
        
        logger.info(f"Initialized {self.__class__.__name__} for domain {domain.name}")
    
    async def process_data(self, data_point: Dict) -> None:
        """Process an incoming data point."""
        # Add timestamp if not present
        if "timestamp" not in data_point:
            data_point["timestamp"] = datetime.utcnow().isoformat()
            
        # Add to data storage
        self.data_storage.append(data_point)
        self.metrics["data_points_processed"] += 1
        
        # Prune old data if needed
        if len(self.data_storage) > self.max_data_points:
            self._prune_old_data()
    
    async def learn(self) -> Dict:
        """Perform a learning cycle and return results."""
        start_time = datetime.utcnow()
        
        try:
            # Process should be implemented by subclasses
            result = await self._learn_implementation()
            
            # Update metrics
            self.last_learning_cycle = datetime.utcnow()
            self.metrics["learning_cycles_completed"] += 1
            self.metrics["last_cycle_duration"] = (
                datetime.utcnow() - start_time).total_seconds()
            
            # Store learning results
            self.learning_results = {
                **result,
                "timestamp": self.last_learning_cycle.isoformat()
            }
            
            return self.learning_results
        
        except Exception as e:
            logger.error(f"Learning cycle failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def generate_improvement(self) -> Optional[Dict]:
        """Generate an improvement based on learning results."""
        # Should be implemented by subclasses
        return None
    
    async def get_metrics(self) -> Dict:
        """Get current metrics for this learning strategy."""
        return {
            **self.metrics,
            "data_points_stored": len(self.data_storage),
            "last_learning_cycle": self.last_learning_cycle.isoformat() 
                if self.last_learning_cycle else None
        }
    
    async def get_learning_data(self) -> Dict:
        """Get learning data and results."""
        return {
            "domain": self.domain.name,
            "strategy": self.__class__.__name__,
            "data_sample": self.data_storage[-10:] if self.data_storage else [],
            "data_count": len(self.data_storage),
            "learning_results": self.learning_results,
            "metrics": await self.get_metrics()
        }
    
    def _prune_old_data(self) -> None:
        """Remove old data points to stay within limits."""
        # Remove oldest data points if we have too many
        if len(self.data_storage) > self.max_data_points:
            self.data_storage = self.data_storage[-self.max_data_points:]
    
    async def _learn_implementation(self) -> Dict:
        """Learning implementation to be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement _learn_implementation")


class OperationalLearning(LearningStrategy):
    """
    Operational learning strategy focused on optimizing existing system components.
    Used for performance optimization and stability improvement.
    """
    
    async def _learn_implementation(self) -> Dict:
        """Implement operational learning."""
        if not self.data_storage:
            return {
                "success": False,
                "message": "No data available for learning"
            }
        
        # Group data by component
        components = {}
        for data_point in self.data_storage:
            component = data_point.get("component", "unknown")
            if component not in components:
                components[component] = []
            components[component].append(data_point)
        
        # Analyze each component
        insights = {}
        for component, data_points in components.items():
            insights[component] = self._analyze_component_data(component, data_points)
        
        return {
            "success": True,
            "components_analyzed": len(components),
            "insights": insights,
            "improvement_opportunities": self._identify_improvement_opportunities(insights)
        }
    
    def _analyze_component_data(self, component: str, data_points: List[Dict]) -> Dict:
        """Analyze data for a specific component."""
        # Implementation depends on the domain
        if self.domain == LearningDomain.PERFORMANCE:
            return self._analyze_performance(component, data_points)
        elif self.domain == LearningDomain.STABILITY:
            return self._analyze_stability(component, data_points)
        else:
            return {"message": "Domain not supported by operational learning"}
    
    def _analyze_performance(self, component: str, data_points: List[Dict]) -> Dict:
        """Analyze performance data."""
        # Extract metrics
        metrics = {}
        for point in data_points:
            for metric_name, value in point.get("metrics", {}).items():
                if metric_name not in metrics:
                    metrics[metric_name] = []
                metrics[metric_name].append(value)
        
        # Calculate statistics for each metric
        stats = {}
        for metric_name, values in metrics.items():
            if values:
                stats[metric_name] = {
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "count": len(values)
                }
        
        return {
            "metrics_analyzed": len(stats),
            "statistics": stats
        }
    
    def _analyze_stability(self, component: str, data_points: List[Dict]) -> Dict:
        """Analyze stability data (errors, crashes, etc.)."""
        # Group by error type
        error_types = {}
        for point in data_points:
            error_type = point.get("error_type", "unknown")
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(point)
        
        # Analyze each error type
        error_analysis = {}
        for error_type, errors in error_types.items():
            error_analysis[error_type] = {
                "count": len(errors),
                "first_occurrence": min(e.get("timestamp", "") for e in errors),
                "last_occurrence": max(e.get("timestamp", "") for e in errors),
                "common_contexts": self._find_common_contexts(errors)
            }
        
        return {
            "error_types": len(error_types),
            "total_errors": len(data_points),
            "error_analysis": error_analysis
        }
    
    def _find_common_contexts(self, errors: List[Dict]) -> List[str]:
        """Find common contexts in error reports."""
        contexts = {}
        for error in errors:
            context = error.get("context", "unknown")
            contexts[context] = contexts.get(context, 0) + 1
        
        # Return the most common contexts
        return sorted(contexts.keys(), key=lambda k: contexts[k], reverse=True)[:3]
    
    def _identify_improvement_opportunities(self, insights: Dict) -> List[Dict]:
        """Identify improvement opportunities from insights."""
        opportunities = []
        
        if self.domain == LearningDomain.PERFORMANCE:
            # Look for components with performance bottlenecks
            for component, analysis in insights.items():
                for metric, stats in analysis.get("statistics", {}).items():
                    if metric == "response_time" and stats.get("avg", 0) > 100:
                        opportunities.append({
                            "component": component,
                            "metric": metric,
                            "current_value": stats["avg"],
                            "target_value": stats["avg"] * 0.7,  # 30% improvement
                            "priority": "high" if stats["avg"] > 500 else "medium"
                        })
        
        elif self.domain == LearningDomain.STABILITY:
            # Look for components with recurring errors
            for component, analysis in insights.items():
                for error_type, error_stats in analysis.get("error_analysis", {}).items():
                    if error_stats.get("count", 0) > 5:
                        opportunities.append({
                            "component": component,
                            "error_type": error_type,
                            "occurrence_count": error_stats["count"],
                            "priority": "high" if error_stats["count"] > 10 else "medium"
                        })
        
        return opportunities
    
    async def generate_improvement(self) -> Optional[Dict]:
        """Generate an improvement based on learning results."""
        if not self.learning_results.get("success", False):
            return None
        
        opportunities = self.learning_results.get("improvement_opportunities", [])
        if not opportunities:
            return None
        
        # Sort opportunities by priority
        sorted_opportunities = sorted(
            opportunities, 
            key=lambda o: 0 if o.get("priority") == "high" else 1
        )
        
        # Take the highest priority opportunity
        opportunity = sorted_opportunities[0]
        
        # Generate improvement
        improvement = {
            "id": f"imp-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "component": opportunity.get("component", "unknown"),
            "domain": self.domain.name,
            "description": self._generate_improvement_description(opportunity),
            "changes": self._generate_improvement_changes(opportunity),
            "timestamp": datetime.utcnow().isoformat(),
            "opportunity": opportunity
        }
        
        self.metrics["improvements_generated"] += 1
        
        return improvement
    
    def _generate_improvement_description(self, opportunity: Dict) -> str:
        """Generate a description for an improvement."""
        if self.domain == LearningDomain.PERFORMANCE:
            return (
                f"Performance optimization for {opportunity.get('component')} "
                f"to improve {opportunity.get('metric')} from "
                f"{opportunity.get('current_value'):.2f} to "
                f"{opportunity.get('target_value'):.2f}"
            )
        elif self.domain == LearningDomain.STABILITY:
            return (
                f"Stability improvement for {opportunity.get('component')} "
                f"to address {opportunity.get('error_type')} errors that have "
                f"occurred {opportunity.get('occurrence_count')} times"
            )
        else:
            return f"System improvement for {opportunity.get('component')}"
    
    def _generate_improvement_changes(self, opportunity: Dict) -> Dict:
        """Generate the actual changes for an improvement."""
        # In a real implementation, this would generate actual code changes
        # For now, we'll provide a placeholder
        return {
            "type": "placeholder",
            "description": "This is a placeholder for actual code changes"
        }


class ExperimentalLearning(LearningStrategy):
    """
    Experimental learning strategy that explores new approaches.
    Used for security enhancement and user interaction improvement.
    """
    
    async def _learn_implementation(self) -> Dict:
        """Implement experimental learning."""
        if not self.data_storage:
            return {
                "success": False,
                "message": "No data available for learning"
            }
        
        # Analyze patterns in the data
        patterns = self._analyze_patterns()
        
        # Generate experiments based on patterns
        experiments = self._generate_experiments(patterns)
        
        return {
            "success": True,
            "patterns_found": len(patterns),
            "experiments_generated": len(experiments),
            "patterns": patterns,
            "experiments": experiments
        }
    
    def _analyze_patterns(self) -> List[Dict]:
        """Analyze patterns in the data."""
        patterns = []
        
        if self.domain == LearningDomain.SECURITY:
            # Look for security patterns
            # Count security events by type
            event_counts = {}
            for data_point in self.data_storage:
                event_type = data_point.get("event_type", "unknown")
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            # Create patterns for common events
            for event_type, count in event_counts.items():
                if count > 3:
                    patterns.append({
                        "type": "security_event_frequency",
                        "event_type": event_type,
                        "count": count,
                        "significance": "high" if count > 10 else "medium"
                    })
        
        elif self.domain == LearningDomain.USER_INTERACTION:
            # Look for user interaction patterns
            # Group interactions by interface
            interfaces = {}
            for data_point in self.data_storage:
                interface = data_point.get("interface", "unknown")
                if interface not in interfaces:
                    interfaces[interface] = []
                interfaces[interface].append(data_point)
            
            # Create patterns for each interface
            for interface, interactions in interfaces.items():
                # Calculate average satisfaction
                satisfactions = [i.get("satisfaction", 0) for i in interactions if "satisfaction" in i]
                if satisfactions:
                    avg_satisfaction = sum(satisfactions) / len(satisfactions)
                    patterns.append({
                        "type": "user_satisfaction",
                        "interface": interface,
                        "average_satisfaction": avg_satisfaction,
                        "sample_size": len(satisfactions),
                        "significance": "high" if avg_satisfaction < 3 else "medium" if avg_satisfaction < 4 else "low"
                    })
        
        return patterns
    
    def _generate_experiments(self, patterns: List[Dict]) -> List[Dict]:
        """Generate experiments based on patterns."""
        experiments = []
        
        for pattern in patterns:
            if pattern.get("significance") in ["high", "medium"]:
                if self.domain == LearningDomain.SECURITY:
                    experiments.append({
                        "id": f"exp-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(experiments)}",
                        "type": "security_enhancement",
                        "target_event": pattern.get("event_type"),
                        "approach": "enhanced_validation" if "validation" in pattern.get("event_type", "").lower() else "access_control",
                        "priority": "high" if pattern.get("significance") == "high" else "medium"
                    })
                
                elif self.domain == LearningDomain.USER_INTERACTION:
                    if pattern.get("type") == "user_satisfaction" and pattern.get("average_satisfaction", 5) < 4:
                        experiments.append({
                            "id": f"exp-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{len(experiments)}",
                            "type": "interface_improvement",
                            "target_interface": pattern.get("interface"),
                            "approach": "simplification" if pattern.get("average_satisfaction", 0) < 3 else "refinement",
                            "priority": "high" if pattern.get("significance") == "high" else "medium"
                        })
        
        return experiments
    
    async def generate_improvement(self) -> Optional[Dict]:
        """Generate an improvement based on experimental results."""
        if not self.learning_results.get("success", False):
            return None
        
        experiments = self.learning_results.get("experiments", [])
        if not experiments:
            return None
        
        # Sort experiments by priority
        sorted_experiments = sorted(
            experiments, 
            key=lambda e: 0 if e.get("priority") == "high" else 1
        )
        
        # Take the highest priority experiment
        experiment = sorted_experiments[0]
        
        # Generate improvement
        improvement = {
            "id": f"imp-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "domain": self.domain.name,
            "description": self._generate_experiment_description(experiment),
            "changes": self._generate_experiment_changes(experiment),
            "timestamp": datetime.utcnow().isoformat(),
            "experiment": experiment
        }
        
        # Determine the component based on the experiment type
        if self.domain == LearningDomain.SECURITY:
            improvement["component"] = "security_manager"
        elif self.domain == LearningDomain.USER_INTERACTION:
            improvement["component"] = f"{experiment.get('target_interface', 'unknown')}_interface"
        
        self.metrics["improvements_generated"] += 1
        
        return improvement
    
    def _generate_experiment_description(self, experiment: Dict) -> str:
        """Generate a description for an experiment-based improvement."""
        if self.domain == LearningDomain.SECURITY:
            return (
                f"Security enhancement to address {experiment.get('target_event')} "
                f"events using {experiment.get('approach')} techniques"
            )
        elif self.domain == LearningDomain.USER_INTERACTION:
            return (
                f"User interface improvement for {experiment.get('target_interface')} "
                f"using {experiment.get('approach')} approach"
            )
        else:
            return f"Experimental improvement based on pattern analysis"
    
    def _generate_experiment_changes(self, experiment: Dict) -> Dict:
        """Generate the actual changes for an experiment-based improvement."""
        # In a real implementation, this would generate actual changes
        # For now, we'll provide a placeholder
        return {
            "type": "placeholder",
            "description": "This is a placeholder for actual implementation changes"
        }
