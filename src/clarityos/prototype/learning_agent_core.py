"""
Learning Agent Core Functionality

This module implements the core learning capabilities of the AI agent
including observation, exploration, experimentation, and knowledge building.
"""

import asyncio
import logging
import random
import time
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


# These methods will be mixed into the LearningAgent class
async def adjust_learning_mode(self):
    """Adjust the current learning mode based on agent state."""
    # Get counts of items in each state
    observation_count = len(self.observations)
    hypothesis_count = len(self.hypotheses)
    experiment_count = len(self.experiments)
    knowledge_count = len(self.knowledge)
    running_experiment_count = len(self._running_experiments)
    
    # Simple state machine logic for mode transitions
    if observation_count < 10:
        # Not enough observations, stay in observation mode
        new_mode = LearningMode.OBSERVATION
    
    elif hypothesis_count < 5:
        # Need more hypotheses, switch to exploration
        new_mode = LearningMode.EXPLORATION
    
    elif running_experiment_count < self.max_concurrent_experiments and hypothesis_count > 0:
        # Run experiments if there are hypotheses to test
        new_mode = LearningMode.EXPERIMENTATION
    
    elif knowledge_count > 0 and knowledge_count % 10 == 0:
        # Periodically apply knowledge to build components
        new_mode = LearningMode.IMPLEMENTATION
    
    elif knowledge_count > 5:
        # Optimize existing components based on knowledge
        new_mode = LearningMode.OPTIMIZATION
    
    else:
        # Default to observation
        new_mode = LearningMode.OBSERVATION
    
    # Also factor in random exploration to avoid getting stuck
    if random.random() < self.exploration_factor:
        new_mode = random.choice(list(LearningMode))
    
    # Log mode changes
    if new_mode != self.current_mode:
        logger.info(f"Learning mode changed: {self.current_mode.value} -> {new_mode.value}")
        self.current_mode = new_mode


async def observe_environment(self):
    """Passively observe the system environment."""
    # In a real system, this would collect metrics and events
    # For the prototype, we'll simulate some basic observations
    
    # Sample resource usage
    await self._create_observation(
        LearningDomain.RESOURCES,
        "Periodic resource usage sampling",
        {
            "cpu_usage": random.uniform(10, 90),
            "memory_usage": random.uniform(20, 80),
            "io_operations": random.randint(10, 1000)
        }
    )
    
    # Request hardware information from the bus
    try:
        response = await system_bus.request_response(
            message_type="hardware.discover",
            content={},
            source=f"learning_agent_{self.agent_id}",
            timeout=5.0
        )
        
        if response and response.content.get("success"):
            devices = response.content.get("devices", {})
            
            # Create observations for each device type
            for device_type, device_list in devices.items():
                await self._create_observation(
                    LearningDomain.HARDWARE,
                    f"Hardware discovery for {device_type}",
                    {
                        "device_type": device_type,
                        "device_count": len(device_list),
                        "devices": device_list
                    }
                )
    
    except Exception as e:
        logger.error(f"Error requesting hardware information: {str(e)}")


async def explore_environment(self):
    """Actively explore the system to gather information."""
    # Choose a domain to explore based on weights
    domain = self._choose_weighted_domain()
    
    logger.info(f"Exploring domain: {domain.value}")
    
    if domain == LearningDomain.HARDWARE:
        # Test hardware capabilities
        await self._explore_hardware()
        
    elif domain == LearningDomain.RESOURCES:
        # Test resource allocation
        await self._explore_resources()
        
    elif domain == LearningDomain.MEMORY:
        # Test memory management
        await self._explore_memory()
        
    elif domain == LearningDomain.STORAGE:
        # Test storage systems
        await self._explore_storage()
        
    elif domain == LearningDomain.SCHEDULING:
        # Test process scheduling
        await self._explore_scheduling()
        
    # Adjust weights to favor less-explored domains
    self._update_exploration_weights(domain)


async def explore_hardware(self):
    """Explore hardware capabilities."""
    # In a real system, would run actual hardware tests
    # For the prototype, simulate some basic exploration
    
    # Choose a random device type
    device_type = random.choice(list(DeviceType))
    
    # Request information for this type
    try:
        response = await system_bus.request_response(
            message_type="hardware.discover",
            content={"device_type": device_type.value},
            source=f"learning_agent_{self.agent_id}",
            timeout=5.0
        )
        
        if response and response.content.get("success"):
            devices = response.content.get("devices", [])
            
            if devices:
                # Create hypotheses about hardware capabilities
                if device_type == DeviceType.CPU:
                    await self._create_hypothesis(
                        LearningDomain.HARDWARE,
                        "CPU cores scale linearly with parallel tasks up to physical core count",
                        confidence=0.5
                    )
                
                elif device_type == DeviceType.MEMORY:
                    await self._create_hypothesis(
                        LearningDomain.MEMORY,
                        "Memory access patterns show locality of reference",
                        confidence=0.6
                    )
    
    except Exception as e:
        logger.error(f"Error exploring hardware: {str(e)}")


async def explore_resources(self):
    """Explore resource management."""
    # In a real system, would test resource allocation
    # For the prototype, create sample hypotheses
    
    await self._create_hypothesis(
        LearningDomain.RESOURCES,
        "Priority-based scheduling improves response time for interactive tasks",
        confidence=0.4
    )
    
    await self._create_hypothesis(
        LearningDomain.RESOURCES,
        "Resource usage follows predictable patterns based on workload type",
        confidence=0.3
    )


async def explore_memory(self):
    """Explore memory management."""
    # For prototype, create sample hypotheses
    
    await self._create_hypothesis(
        LearningDomain.MEMORY,
        "Page replacement algorithms affect cache hit rates",
        confidence=0.5
    )
    
    await self._create_hypothesis(
        LearningDomain.MEMORY,
        "Memory segmentation reduces fragmentation compared to flat allocation",
        confidence=0.4
    )


async def explore_storage(self):
    """Explore storage systems."""
    # For prototype, create sample hypotheses
    
    await self._create_hypothesis(
        LearningDomain.STORAGE,
        "Content-based file organization improves retrieval times for related data",
        confidence=0.3
    )
    
    await self._create_hypothesis(
        LearningDomain.STORAGE,
        "Journal-based file systems recover faster from system failures",
        confidence=0.6
    )


async def explore_scheduling(self):
    """Explore process scheduling."""
    # For prototype, create sample hypotheses
    
    await self._create_hypothesis(
        LearningDomain.SCHEDULING,
        "Preemptive scheduling improves system responsiveness",
        confidence=0.7
    )
    
    await self._create_hypothesis(
        LearningDomain.SCHEDULING,
        "Batch processing benefits from longer time slices",
        confidence=0.5
    )


async def run_experiments(self):
    """Run experiments to test hypotheses."""
    # Check if we can start new experiments
    if len(self._running_experiments) >= self.max_concurrent_experiments:
        return
    
    # Choose a hypothesis to test
    hypothesis_id = self._choose_hypothesis_for_testing()
    if not hypothesis_id:
        return
    
    hypothesis = self.hypotheses[hypothesis_id]
    
    # Create and run an experiment
    experiment_id = self._generate_id("experiment")
    
    # Set up experiment parameters (would be more sophisticated in a real system)
    parameters = {"iterations": 10, "test_type": "simulation"}
    
    experiment = Experiment(
        id=experiment_id,
        hypothesis_id=hypothesis_id,
        description=f"Testing: {hypothesis.description}",
        parameters=parameters,
        expected_outcome="Confirm or reject hypothesis"
    )
    
    self.experiments[experiment_id] = experiment
    self._running_experiments.add(experiment_id)
    
    # Start the experiment in a separate task
    experiment.started_at = time.time()
    asyncio.create_task(self._run_experiment(experiment_id))
    
    logger.info(f"Started experiment {experiment_id} for hypothesis: {hypothesis.description}")


async def run_experiment(self, experiment_id: str):
    """Run a single experiment."""
    try:
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return
        
        hypothesis = self.hypotheses.get(experiment.hypothesis_id)
        if not hypothesis:
            return
        
        # Simulate experiment execution time
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # Simulate experiment result (random for prototype)
        # In a real system, would run actual tests with metrics
        success = random.random() > 0.3  # 70% success rate for simulation
        
        # Update experiment
        experiment.completed_at = time.time()
        experiment.success = success
        experiment.result = {
            "measured_values": {
                "metric_1": random.uniform(0, 100),
                "metric_2": random.uniform(0, 100)
            },
            "deviation_from_expected": random.uniform(0, 50),
            "conclusion": "Results support hypothesis" if success else "Results contradict hypothesis"
        }
        
        # Update hypothesis
        hypothesis.tests_run += 1
        hypothesis.last_tested = time.time()
        if success:
            hypothesis.successful_tests += 1
            
            # Increase confidence with successful tests
            confidence_gain = 0.1 * (1.0 - hypothesis.confidence)
            hypothesis.confidence = min(1.0, hypothesis.confidence + confidence_gain)
        else:
            # Decrease confidence with failed tests
            confidence_loss = 0.2 * hypothesis.confidence
            hypothesis.confidence = max(0.0, hypothesis.confidence - confidence_loss)
        
        # If confidence is high enough, convert to knowledge
        if hypothesis.confidence >= self.min_confidence_threshold:
            await self._create_knowledge_from_hypothesis(hypothesis.id)
        
        logger.info(
            f"Experiment {experiment_id} completed: "
            f"{'success' if success else 'failure'}, "
            f"hypothesis confidence now {hypothesis.confidence:.2f}"
        )
    
    except Exception as e:
        logger.error(f"Error running experiment {experiment_id}: {str(e)}")
    
    finally:
        # Remove from running experiments
        self._running_experiments.discard(experiment_id)


async def cancel_experiment(self, experiment_id: str):
    """Cancel a running experiment."""
    experiment = self.experiments.get(experiment_id)
    if not experiment:
        return
    
    # Mark as completed but unsuccessful
    experiment.completed_at = time.time()
    experiment.success = False
    experiment.result = {"conclusion": "Experiment cancelled"}
    
    # Remove from running list
    self._running_experiments.discard(experiment_id)
    
    logger.info(f"Experiment {experiment_id} cancelled")


async def generate_hypotheses(self):
    """Generate new hypotheses from observations."""
    # Only generate hypotheses periodically
    if random.random() > 0.3:
        return
    
    # In a real system, would use more sophisticated pattern matching
    # For the prototype, simulated basic hypothesis generation
    
    # Get recent observations
    recent_observations = sorted(
        self.observations.values(),
        key=lambda o: o.timestamp,
        reverse=True
    )[:10]
    
    if not recent_observations:
        return
    
    # Choose a random observation to generate a hypothesis from
    observation = random.choice(recent_observations)
    
    # Generate a hypothesis based on domain
    if observation.domain == LearningDomain.HARDWARE:
        if "device_type" in observation.data:
            device_type = observation.data["device_type"]
            
            if device_type == "cpu":
                await self._create_hypothesis(
                    LearningDomain.HARDWARE,
                    "CPU utilization pattern indicates optimization opportunity for parallel tasks",
                    confidence=0.2
                )
            
            elif device_type == "memory":
                await self._create_hypothesis(
                    LearningDomain.MEMORY,
                    "Memory access patterns suggest benefit from predictive prefetching",
                    confidence=0.3
                )
    
    elif observation.domain == LearningDomain.RESOURCES:
        await self._create_hypothesis(
            LearningDomain.RESOURCES,
            "Dynamic resource allocation based on workload type improves efficiency",
            confidence=0.4
        )


async def report_status(self):
    """Report agent status and learning progress."""
    await system_bus.publish(
        message_type="agent.status.update",
        content={
            "agent_id": self.agent_id,
            "status": "running",
            "metrics": {
                "current_mode": self.current_mode.value,
                "observations": len(self.observations),
                "hypotheses": len(self.hypotheses),
                "experiments": len(self.experiments),
                "knowledge_items": len(self.knowledge),
                "running_experiments": len(self._running_experiments)
            }
        },
        source=f"learning_agent_{self.agent_id}",
        priority=MessagePriority.LOW
    )
