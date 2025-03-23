"""
ClarityOS Learning Framework

This package provides learning capabilities for ClarityOS, enabling the system
to adapt and improve through experience.
"""

from clarityos.core.learning_framework import (
    LearningDomain,
    LearningPriority,
    LearningStrategy,
    learning_framework
)

# Import strategy and domain modules
from clarityos.learning import strategies
from clarityos.learning import domains


async def initialize_learning_framework():
    """Initialize the learning framework and start learning processes."""
    return await learning_framework.initialize()


async def submit_learning_task(domain: str, task_type: str, data: dict, priority: str = "MEDIUM", callback: str = None):
    """
    Submit a learning task to the framework.
    
    Args:
        domain: Learning domain (one of the LearningDomain values)
        task_type: Type of learning task 
        data: Data for the learning task
        priority: Priority level (one of the LearningPriority values)
        callback: Optional message type for callback
        
    Returns:
        Tuple of (success, message, task_id)
    """
    return await learning_framework.submit_task(
        domain=LearningDomain(domain),
        task_type=task_type,
        data=data,
        priority=LearningPriority[priority],
        callback=callback
    )


async def submit_pattern(name: str, domain: str, pattern_type: str, data: dict, confidence: float = 0.5):
    """
    Submit a learned pattern to the framework.
    
    Args:
        name: Name of the pattern
        domain: Learning domain (one of the LearningDomain values) 
        pattern_type: Type of pattern
        data: Pattern data
        confidence: Confidence level (0-1)
        
    Returns:
        Tuple of (success, message, pattern_id)
    """
    return await learning_framework.submit_pattern(
        name=name,
        domain=LearningDomain(domain),
        pattern_type=pattern_type,
        data=data,
        confidence=confidence
    )


async def provide_feedback(pattern_id: str, is_positive: bool, confidence_adjustment: float = 0.1, details: dict = None):
    """
    Provide feedback on a learned pattern.
    
    Args:
        pattern_id: ID of the pattern
        is_positive: Whether the feedback is positive
        confidence_adjustment: Amount to adjust confidence
        details: Additional feedback details
        
    Returns:
        True if successful
    """
    return await learning_framework.provide_feedback(
        pattern_id=pattern_id,
        is_positive=is_positive,
        confidence_adjustment=confidence_adjustment,
        details=details
    )


async def get_knowledge(domain: str, key: str = None):
    """
    Get knowledge from the knowledge base.
    
    Args:
        domain: Knowledge domain
        key: Optional specific key within domain
        
    Returns:
        Knowledge data or None if not found
    """
    return await learning_framework.get_knowledge(domain, key)


async def set_knowledge(domain: str, key: str, value):
    """
    Set knowledge in the knowledge base.
    
    Args:
        domain: Knowledge domain
        key: Key within domain
        value: Value to store
        
    Returns:
        True if successful
    """
    return await learning_framework.set_knowledge(domain, key, value)


async def query_patterns(domain: str = None, pattern_type: str = None, min_confidence: float = 0.0):
    """
    Query for patterns matching specified criteria.
    
    Args:
        domain: Optional domain to filter by
        pattern_type: Optional pattern type to filter by
        min_confidence: Minimum confidence level
        
    Returns:
        List of matching patterns
    """
    domain_obj = None
    if domain:
        domain_obj = LearningDomain(domain)
        
    return await learning_framework.query_patterns(
        domain=domain_obj,
        pattern_type=pattern_type,
        min_confidence=min_confidence
    )


async def shutdown_learning_framework():
    """Shut down the learning framework."""
    return await learning_framework.shutdown()
