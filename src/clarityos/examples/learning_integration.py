"""
Learning Framework Integration Example

This module demonstrates how the Learning Framework integrates with other
ClarityOS components to enable system-wide learning and adaptation.
"""

import asyncio
import logging
from typing import Dict, List, Any

from ..core.message_bus import system_bus
from ..learning import (
    initialize_learning_framework,
    submit_learning_task,
    submit_pattern,
    provide_feedback,
    query_patterns,
    get_knowledge,
    set_knowledge
)
from ..core.memory_manager import memory_manager
from ..core.agent_manager import agent_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def resource_optimization_example():
    """Example of learning to optimize resource allocation."""
    logger.info("Starting resource optimization learning example")
    
    # Step 1: Collect resource usage data (simulated)
    resource_data = {
        "resource_type": "memory",
        "usage_history": [
            {"timestamp": 1616509200, "usage": 65, "process": "intent_agent"},
            {"timestamp": 1616512800, "usage": 82, "process": "intent_agent"},
            {"timestamp": 1616520000, "usage": 90, "process": "intent_agent"},
        ]
    }
    
    # Step 2: Submit learning task to analyze resource usage
    success, message, task_id = await submit_learning_task(
        domain="SYSTEM",
        task_type="resource_usage",
        data=resource_data,
        priority="HIGH"
    )
    
    if success:
        logger.info(f"Submitted resource learning task: {message}")
        
        # Step 3: Query for patterns related to memory usage
        await asyncio.sleep(1)  # Give time for processing
        patterns = await query_patterns(domain="SYSTEM", pattern_type="resource_peak")
        
        if patterns:
            logger.info(f"Found {len(patterns)} resource usage patterns")
            
            # Step 4: Use patterns to optimize memory allocation
            pattern = patterns[0]
            pattern_id = pattern["id"]
            
            # Step 5: Provide feedback on the pattern's usefulness
            await provide_feedback(
                pattern_id=pattern_id,
                is_positive=True,
                details={"applied_to": "memory_allocation"}
            )
            
            # Step 6: Store knowledge about the optimization
            await set_knowledge(
                domain="resource_optimizations",
                key="intent_agent_memory",
                value={
                    "pattern_id": pattern_id,
                    "recommended_allocation": 512  # MB
                }
            )


async def user_preference_example():
    """Example of learning user preferences."""
    logger.info("Starting user preference learning example")
    
    # Step 1: Collect user interaction data (simulated)
    user_data = {
        "user_id": "user-123",
        "interactions": [
            {"action": "set_theme", "value": "dark", "timestamp": 1616509200},
            {"action": "adjust_notification", "value": "minimal", "timestamp": 1616512800},
            {"action": "organize_by", "value": "project", "timestamp": 1616516400}
        ]
    }
    
    # Step 2: Submit learning task for user preference analysis
    success, message, task_id = await submit_learning_task(
        domain="USER",
        task_type="preference_analysis",
        data=user_data,
        priority="MEDIUM"
    )
    
    if success:
        logger.info(f"Submitted user preference task: {message}")
        
        # Step 3: Create a preference pattern based on analysis
        pattern_id = await submit_pattern(
            name="user_interface_preferences",
            domain="USER",
            pattern_type="ui_preferences",
            data={
                "theme": "dark",
                "notification_level": "minimal",
                "organization": "project"
            },
            confidence=0.8
        )
        
        # Step 4: Store the preference knowledge
        await set_knowledge(
            domain="user_preferences",
            key="user-123",
            value={
                "ui": {
                    "theme": "dark",
                    "notification_level": "minimal",
                    "organization": "project"
                }
            }
        )


async def intent_learning_example():
    """Example of learning from natural language interactions."""
    logger.info("Starting intent learning example")
    
    # Step 1: Record an intent correction scenario
    intent_data = {
        "text": "show me system performance",
        "original_intent": "system.help",
        "corrected_intent": "system.performance.show",
        "context": {"previous_topic": "monitoring"}
    }
    
    # Step 2: Submit learning task for intent correction
    success, message, task_id = await submit_learning_task(
        domain="INTENT",
        task_type="intent_correction",
        data=intent_data,
        priority="HIGH"
    )
    
    if success:
        logger.info(f"Submitted intent learning task: {message}")
        
        # Step 3: Apply the learned correction to future intent parsing
        await set_knowledge(
            domain="intent_corrections",
            key="show me system performance",
            value="system.performance.show"
        )


async def main():
    """Run the learning integration examples."""
    # Initialize the learning framework
    await initialize_learning_framework()
    logger.info("Learning framework initialized")
    
    # Run the examples
    await resource_optimization_example()
    await user_preference_example()
    await intent_learning_example()
    
    # Show how other components can use learned knowledge
    memory_knowledge = await get_knowledge("resource_optimizations", "intent_agent_memory")
    if memory_knowledge:
        logger.info(f"Memory optimization knowledge: {memory_knowledge}")
        
        # Apply the optimization (simulated)
        logger.info(f"Applying learned memory allocation: {memory_knowledge['recommended_allocation']}MB")
    
    user_knowledge = await get_knowledge("user_preferences", "user-123")
    if user_knowledge:
        logger.info(f"User preference knowledge: {user_knowledge}")
        
        # Apply the preferences (simulated)
        logger.info(f"Applying learned UI preferences: theme={user_knowledge['ui']['theme']}")
    
    intent_knowledge = await get_knowledge("intent_corrections", "show me system performance")
    if intent_knowledge:
        logger.info(f"Intent correction knowledge: '{intent_knowledge}'")
        
        # Apply the intent correction (simulated)
        logger.info(f"Applying learned intent correction: parsed as '{intent_knowledge}'")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
