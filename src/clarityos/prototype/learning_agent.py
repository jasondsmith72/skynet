"""
Learning Agent for AI OS

This module implements a learning agent that can explore and understand
its computing environment, then incrementally build and improve OS components
based on what it learns.
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from clarityos.core.message_bus import MessagePriority, system_bus
from clarityos.prototype.hardware_bus import DeviceType
from clarityos.prototype.learning_models import (
    LearningMode, LearningDomain, Hypothesis, Observation, 
    Experiment, KnowledgeItem
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LearningAgent:
    """
    An agent that learns about the computing environment and builds OS components.
    
    This agent uses a scientific method approach:
    1. Observe the environment
    2. Form hypotheses about system behavior
    3. Design experiments to test hypotheses
    4. Run experiments and analyze results
    5. Update knowledge based on results
    6. Apply knowledge to build or improve components
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.config = config
        
        # Knowledge base
        self.observations: Dict[str, Observation] = {}
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.experiments: Dict[str, Experiment] = {}
        self.knowledge: Dict[str, KnowledgeItem] = {}
        
        # Current state
        self.current_mode = LearningMode.OBSERVATION
        self.current_domains = set(LearningDomain)
        self.exploration_weights = {domain: 1.0 for domain in LearningDomain}
        
        # Limits and settings
        self.max_concurrent_experiments = config.get("max_concurrent_experiments", 3)
        self.min_confidence_threshold = config.get("min_confidence_threshold", 0.7)
        self.exploration_factor = config.get("exploration_factor", 0.3)
        self.observation_interval = config.get("observation_interval", 5.0)
        
        # Internal state
        self._running_experiments: Set[str] = set()
        self._next_id_counter = 0
        self._shutdown_event = asyncio.Event()
        self._subscription_ids = []
    
    async def start(self):
        """Initialize the agent and subscribe to relevant messages."""
        logger.info(f"Starting LearningAgent (ID: {self.agent_id})")
        
        # Subscribe to messages
        self._subscription_ids.append(
            system_bus.subscribe(
                "hardware.device.added",
                self._handle_device_added,
                f"learning_agent_{self.agent_id}"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "hardware.discovery.complete",
                self._handle_discovery_complete,
                f"learning_agent_{self.agent_id}"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "system.resource.status",
                self._handle_resource_status,
                f"learning_agent_{self.agent_id}"
            )
        )
        
        # Report initialization complete
        await system_bus.publish(
            message_type="agent.status.update",
            content={
                "agent_id": self.agent_id,
                "status": "running",
                "message": "Learning agent initialized"
            },
            source=f"learning_agent_{self.agent_id}"
        )
    
    async def stop(self):
        """Clean up and stop the agent."""
        logger.info(f"Stopping LearningAgent (ID: {self.agent_id})")
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Unsubscribe from messages
        for subscription_id in self._subscription_ids:
            system_bus.unsubscribe("*", subscription_id)
        
        # Clean up any running experiments
        for experiment_id in list(self._running_experiments):
            await self._cancel_experiment(experiment_id)
        
        # Report shutdown
        await system_bus.publish(
            message_type="agent.status.update",
            content={
                "agent_id": self.agent_id,
                "status": "stopped",
                "message": "Learning agent stopped"
            },
            source=f"learning_agent_{self.agent_id}"
        )
    
    async def run(self):
        """Main agent loop for continuous learning."""
        while not self._shutdown_event.is_set():
            try:
                # Adjust learning mode based on current state
                await self._adjust_learning_mode()
                
                # Perform actions based on current mode
                if self.current_mode == LearningMode.OBSERVATION:
                    await self._observe_environment()
                
                elif self.current_mode == LearningMode.EXPLORATION:
                    await self._explore_environment()
                
                elif self.current_mode == LearningMode.EXPERIMENTATION:
                    await self._run_experiments()
                
                elif self.current_mode == LearningMode.IMPLEMENTATION:
                    await self._implement_components()
                
                elif self.current_mode == LearningMode.OPTIMIZATION:
                    await self._optimize_components()
                
                # Generate new hypotheses from observations
                await self._generate_hypotheses()
                
                # Report status
                await self._report_status()
                
                # Wait for next cycle
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), self.observation_interval)
                except asyncio.TimeoutError:
                    pass
                
            except Exception as e:
                logger.error(f"Error in LearningAgent main loop: {str(e)}", exc_info=True)
                
                # Brief pause to avoid tight error loops
                await asyncio.sleep(1.0)
    
    # Message handlers
    
    async def _handle_device_added(self, message):
        """Handle device addition notifications."""
        content = message.content
        await self._create_observation(
            LearningDomain.HARDWARE,
            f"New device detected: {content.get('device_type')}",
            content
        )
    
    async def _handle_discovery_complete(self, message):
        """Handle hardware discovery completion notifications."""
        content = message.content
        await self._create_observation(
            LearningDomain.HARDWARE,
            "Hardware discovery completed",
            content
        )
    
    async def _handle_resource_status(self, message):
        """Handle resource status updates."""
        content = message.content
        await self._create_observation(
            LearningDomain.RESOURCES,
            "Resource status update",
            content
        )
    
    # Learning modes will be implemented in learning_agent_core.py
    # Component implementation will be defined in learning_agent_implementation.py
    # Helper methods will be defined in learning_agent_utils.py
