"""
AI Talent Integration Extensions

This module extends the talent integration system with additional functionality
including talent evaluation, learning, and orchestration.
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple, Set, Union

from ..core.message_bus import MessagePriority, system_bus
from .talent_models import (
    TalentDomain, TalentLevel, IntegrationStatus,
    TalentCapability, AITalent, TalentRequest, TalentEvaluation,
    TalentLearningSession, KnowledgeTransfer, TalentOrchestrationTask
)
from .talent_execution_part2 import generate_knowledge_from_talent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# These methods will be mixed into the TalentIntegrationSystem class
async def find_best_talent_for_task(self, domain: TalentDomain, task_description: str) -> Optional[Tuple[str, str, TalentCapability]]:
    """
    Find the best talent for a specific task.
    
    Args:
        domain: Task domain
        task_description: Description of the task
        
    Returns:
        Tuple of (talent_id, talent_name, capability) or None if no suitable talent found
    """
    # Get all capabilities in the domain
    capabilities = self.get_capabilities_by_domain(domain)
    
    if not capabilities:
        return None
    
    # In a real system, would perform semantic matching against the task description
    # For the prototype, just return the highest-level capability
    return capabilities[0]


async def learn_from_talent(
    self,
    talent_id: str,
    capability_id: str,
    learning_parameters: Dict[str, Any] = None
) -> Tuple[bool, str, Optional[TalentLearningSession]]:
    """
    Create a learning session where the core OS AI learns from a specialized talent.
    
    Args:
        talent_id: ID of the talent to learn from
        capability_id: ID of the specific capability
        learning_parameters: Parameters for the learning session
        
    Returns:
        Tuple of (success, message, session)
    """
    # Check if talent exists
    talent = self.talents.get(talent_id)
    if not talent:
        return False, f"Talent with ID {talent_id} not found", None
    
    # Check if capability exists
    capability = talent.capabilities.get(capability_id)
    if not capability:
        return False, f"Capability with ID {capability_id} not found for talent {talent.name}", None
    
    # Create learning session
    session_id = self._generate_id("learning_session")
    session = TalentLearningSession(
        id=session_id,
        talent_id=talent_id,
        capability_id=capability_id,
        start_time=time.time(),
        learning_examples=[],
        knowledge_before={},
        knowledge_after={}
    )
    
    # Execute learning session (in real system, would be much more sophisticated)
    try:
        # Set up parameters for learning example
        example_params = learning_parameters or {}
        example_params.setdefault("learning_mode", "demonstration")
        
        # Create a request to generate example content
        request_id = self._generate_id("request")
        request = TalentRequest(
            id=request_id,
            talent_id=talent_id,
            capability_id=capability_id,
            parameters=example_params,
            context={"purpose": "learning"}
        )
        
        # Execute the request
        result = await execute_talent_request(request, talent, capability)
        
        # Extract knowledge from the result
        knowledge = generate_knowledge_from_talent(
            talent_id, capability_id, capability.domain.value, result
        )
        
        # Add example to session
        session.learning_examples.append({
            "request": example_params,
            "result": result,
            "knowledge_extracted": knowledge
        })
        
        # Update session knowledge
        session.knowledge_after = {
            "knowledge_items": knowledge.get("knowledge_items", []),
            "integration_status": "pending"
        }
        
        # Update improvement metrics (simulated)
        session.improvement_metrics = {
            "capability_improvement": random.uniform(0.1, 0.3),
            "knowledge_expansion": random.uniform(0.05, 0.2),
            "confidence": random.uniform(0.7, 0.9)
        }
        
        # Complete the session
        session.end_time = time.time()
        session.status = "completed"
        
        # Create knowledge transfer records
        for item in knowledge.get("knowledge_items", []):
            transfer_id = self._generate_id("knowledge_transfer")
            transfer = KnowledgeTransfer(
                id=transfer_id,
                source_talent_id=talent_id,
                source_capability_id=capability_id,
                domain=capability.domain,
                description=item.get("description", "Knowledge transfer"),
                content=item,
                confidence=item.get("confidence", 0.7)
            )
            
            # In a real system, would store these
            logger.info(f"Created knowledge transfer: {transfer_id}")
            
            # Announce knowledge transfer
            await system_bus.publish(
                message_type="learning.knowledge_transfer",
                content={
                    "transfer_id": transfer_id,
                    "talent_id": talent_id,
                    "capability_id": capability_id,
                    "domain": capability.domain.value,
                    "description": transfer.description,
                    "confidence": transfer.confidence
                },
                source="talent_integration",
                priority=MessagePriority.NORMAL
            )
        
        return True, "Learning session completed successfully", session
        
    except Exception as e:
        logger.error(f"Error in learning session: {str(e)}")
        session.end_time = time.time()
        session.status = "failed"
        return False, f"Learning session failed: {str(e)}", session


async def orchestrate_multi_talent_task(
    self,
    task_name: str,
    task_description: str,
    subtasks: List[Dict[str, Any]],
    dependencies: Dict[str, List[str]] = None
) -> Tuple[bool, str, Optional[TalentOrchestrationTask]]:
    """
    Orchestrate a complex task that requires multiple AI talents.
    
    Args:
        task_name: Name of the task
        task_description: Description of the task
        subtasks: List of subtask specifications
        dependencies: Dictionary mapping subtask IDs to lists of prerequisite subtask IDs
        
    Returns:
        Tuple of (success, message, task)
    """
    # Create task
    task_id = self._generate_id("orchestration_task")
    task = TalentOrchestrationTask(
        id=task_id,
        name=task_name,
        description=task_description,
        subtasks=subtasks,
        assigned_talents={},
        dependencies=dependencies or {}
    )
    
    # Assign talents to subtasks
    for i, subtask in enumerate(subtasks):
        subtask_id = subtask.get("id", f"subtask_{i}")
        subtask_domain = subtask.get("domain")
        subtask_description = subtask.get("description", "")
        
        # Find best talent for this subtask
        try:
            domain_enum = TalentDomain(subtask_domain)
            talent_info = await self.find_best_talent_for_task(domain_enum, subtask_description)
            
            if talent_info:
                talent_id, _, _ = talent_info
                task.assigned_talents[subtask_id] = talent_id
            else:
                logger.warning(f"No suitable talent found for subtask {subtask_id} in domain {subtask_domain}")
        
        except (ValueError, KeyError) as e:
            logger.error(f"Error assigning talent for subtask {subtask_id}: {str(e)}")
    
    # Check if all required subtasks have assigned talents
    unassigned = []
    for i, subtask in enumerate(subtasks):
        subtask_id = subtask.get("id", f"subtask_{i}")
        if subtask_id not in task.assigned_talents:
            unassigned.append(subtask_id)
    
    if unassigned:
        msg = f"Could not assign talents for subtasks: {', '.join(unassigned)}"
        return False, msg, task
    
    # Start task execution
    asyncio.create_task(self._execute_orchestration_task(task))
    
    return True, f"Orchestration task {task_id} created and started", task


async def _execute_orchestration_task(self, task: TalentOrchestrationTask) -> None:
    """
    Execute an orchestration task by running subtasks in the correct order.
    
    Args:
        task: The orchestration task to execute
    """
    try:
        # Mark task as started
        task.status = "running"
        task.started_at = time.time()
        
        # Announce task start
        await system_bus.publish(
            message_type="orchestration.task.started",
            content={
                "task_id": task.id,
                "task_name": task.name,
                "subtask_count": len(task.subtasks)
            },
            source="talent_integration",
            priority=MessagePriority.NORMAL
        )
        
        # Create sets to track subtask status
        completed_subtasks = set()
        running_subtasks = set()
        
        # Execute subtasks in proper order
        while len(completed_subtasks) < len(task.subtasks):
            # Find subtasks that can be started
            for i, subtask in enumerate(task.subtasks):
                subtask_id = subtask.get("id", f"subtask_{i}")
                
                # Skip if already completed or running
                if subtask_id in completed_subtasks or subtask_id in running_subtasks:
                    continue
                
                # Check if dependencies are satisfied
                dependencies = task.dependencies.get(subtask_id, [])
                if all(dep in completed_subtasks for dep in dependencies):
                    # Dependencies satisfied, can start this subtask
                    running_subtasks.add(subtask_id)
                    
                    # Start subtask execution
                    asyncio.create_task(
                        self._execute_subtask(task, subtask, subtask_id, completed_subtasks, running_subtasks)
                    )
            
            # Wait for some progress
            await asyncio.sleep(1.0)
            
            # Check for timeout (in a real system, would have proper timeout handling)
            if time.time() - task.started_at > 300:  # 5 minute timeout
                logger.warning(f"Orchestration task {task.id} timed out")
                task.status = "failed"
                task.completed_at = time.time()
                
                # Announce task failure
                await system_bus.publish(
                    message_type="orchestration.task.failed",
                    content={
                        "task_id": task.id,
                        "task_name": task.name,
                        "error": "Execution timed out"
                    },
                    source="talent_integration",
                    priority=MessagePriority.HIGH
                )
                
                return
        
        # All subtasks completed
        task.status = "completed"
        task.completed_at = time.time()
        
        # Announce task completion
        await system_bus.publish(
            message_type="orchestration.task.completed",
            content={
                "task_id": task.id,
                "task_name": task.name,
                "duration": task.completed_at - task.started_at,
                "results_summary": "All subtasks completed successfully"  # In a real system, would have actual summary
            },
            source="talent_integration",
            priority=MessagePriority.NORMAL
        )
    
    except Exception as e:
        logger.error(f"Error in orchestration task {task.id}: {str(e)}")
        task.status = "failed"
        task.completed_at = time.time()
        
        # Announce task failure
        await system_bus.publish(
            message_type="orchestration.task.failed",
            content={
                "task_id": task.id,
                "task_name": task.name,
                "error": str(e)
            },
            source="talent_integration",
            priority=MessagePriority.HIGH
        )


async def _execute_subtask(
    self,
    task: TalentOrchestrationTask,
    subtask: Dict[str, Any],
    subtask_id: str,
    completed_subtasks: Set[str],
    running_subtasks: Set[str]
) -> None:
    """
    Execute a single subtask within an orchestration task.
    
    Args:
        task: The parent orchestration task
        subtask: The subtask specification
        subtask_id: ID of the subtask
        completed_subtasks: Set of completed subtask IDs (will be updated)
        running_subtasks: Set of running subtask IDs (will be updated)
    """
    try:
        # Get talent for this subtask
        talent_id = task.assigned_talents.get(subtask_id)
        talent = self.talents.get(talent_id)
        
        if not talent:
            raise ValueError(f"Talent {talent_id} not found for subtask {subtask_id}")
        
        # Get capability for this subtask
        capability_id = subtask.get("capability_id")
        if not capability_id:
            # Find first capability in the right domain
            domain = subtask.get("domain")
            for cap_id, cap in talent.capabilities.items():
                if cap.domain.value == domain:
                    capability_id = cap_id
                    break
        
        capability = talent.capabilities.get(capability_id)
        if not capability:
            raise ValueError(f"No suitable capability found for subtask {subtask_id}")
        
        # Set up parameters
        parameters = subtask.get("parameters", {})
        parameters["context"] = {"task_id": task.id, "subtask_id": subtask_id}
        
        # Create request
        request_id = self._generate_id("request")
        request = TalentRequest(
            id=request_id,
            talent_id=talent_id,
            capability_id=capability_id,
            parameters=parameters,
            context={"orchestration_task": task.id, "subtask": subtask_id}
        )
        
        # Execute the request
        result = await execute_talent_request(request, talent, capability)
        
        # Store result in task
        task.results[subtask_id] = {
            "success": True,
            "timestamp": time.time(),
            "result": result
        }
        
        # Update tracking sets
        running_subtasks.discard(subtask_id)
        completed_subtasks.add(subtask_id)
        
        # Announce subtask completion
        await system_bus.publish(
            message_type="orchestration.subtask.completed",
            content={
                "task_id": task.id,
                "subtask_id": subtask_id,
                "talent_id": talent_id,
                "talent_name": talent.name
            },
            source="talent_integration",
            priority=MessagePriority.LOW
        )
        
    except Exception as e:
        logger.error(f"Error in subtask {subtask_id} of task {task.id}: {str(e)}")
        
        # Store error
        task.results[subtask_id] = {
            "success": False,
            "timestamp": time.time(),
            "error": str(e)
        }
        
        # Update tracking sets
        running_subtasks.discard(subtask_id)
        
        # In a real system, would have error handling policy (retry, skip, fail task, etc.)
        # For the prototype, we'll mark it as completed to allow the orchestration to continue
        completed_subtasks.add(subtask_id)
        
        # Announce subtask failure
        await system_bus.publish(
            message_type="orchestration.subtask.failed",
            content={
                "task_id": task.id,
                "subtask_id": subtask_id,
                "error": str(e)
            },
            source="talent_integration",
            priority=MessagePriority.HIGH
        )


# Additional helper methods for the TalentIntegrationSystem

async def _load_benchmarks(self) -> None:
    """Load benchmark definitions for talent evaluation."""
    # In a real system, would load from storage
    # For the prototype, create default benchmarks
    import json
    from clarityos.prototype.talent_models import create_default_benchmarks
    
    benchmark_dict = create_default_benchmarks()
    
    for benchmark_id, benchmark in benchmark_dict.items():
        self.benchmarks[benchmark_id] = {
            "id": benchmark.id,
            "name": benchmark.name,
            "domain": benchmark.domain.value,
            "description": benchmark.description,
            "test_cases": benchmark.test_cases,
            "reference_metrics": benchmark.reference_metrics
        }
    
    logger.info(f"Loaded {len(self.benchmarks)} talent evaluation benchmarks")


async def _evaluate_talent(self, talent_id: str) -> Optional[Dict[str, TalentEvaluation]]:
    """
    Evaluate a talent against benchmarks.
    
    Args:
        talent_id: ID of the talent to evaluate
        
    Returns:
        Dictionary mapping capability IDs to evaluation results, or None if talent not found
    """
    talent = self.talents.get(talent_id)
    if not talent:
        return None
    
    # Update status to evaluating
    old_status = talent.status
    talent.status = IntegrationStatus.EVALUATING
    
    # Announce status change
    await system_bus.publish(
        message_type="talent.status.changed",
        content={
            "talent_id": talent.id,
            "talent_name": talent.name,
            "old_status": old_status.value,
            "new_status": talent.status.value
        },
        source="talent_integration",
        priority=MessagePriority.NORMAL
    )
    
    logger.info(f"Evaluating talent: {talent.name} (ID: {talent.id})")
    
    # Evaluate each capability against benchmarks
    evaluations = {}
    
    for capability_id, capability in talent.capabilities.items():
        # Find relevant benchmarks
        domain_benchmarks = [
            b for b in self.benchmarks.values()
            if b.get("domain") == capability.domain.value
        ]
        
        if not domain_benchmarks:
            continue
        
        # Choose the most appropriate benchmark
        benchmark = domain_benchmarks[0]
        
        # In a real system, would run actual benchmark tests
        # For the prototype, simulate evaluation with random metrics
        await asyncio.sleep(random.uniform(1.0, 3.0))
        
        # Generate simulated evaluation metrics
        metrics = {
            "accuracy": random.uniform(0.7, 1.0),
            "speed": random.uniform(0.5, 1.0),
            "resource_efficiency": random.uniform(0.6, 0.9),
            "reliability": random.uniform(0.8, 1.0)
        }
        
        # Create evaluation result
        evaluation = TalentEvaluation(
            talent_id=talent.id,
            capability_id=capability.id,
            benchmark_id=benchmark["id"],
            benchmark_name=benchmark["name"],
            metrics=metrics,
            examples=[]
        )
        
        evaluations[capability_id] = evaluation
        
        # Update capability performance metrics
        capability.performance_metrics.update(metrics)
    
    # Set talent status based on evaluation results
    if all(e.metrics["accuracy"] > 0.8 for e in evaluations.values()):
        talent.status = IntegrationStatus.INTEGRATED
    else:
        talent.status = IntegrationStatus.DISCOVERED
    
    # Announce evaluation results
    await system_bus.publish(
        message_type="talent.evaluation.complete",
        content={
            "talent_id": talent.id,
            "talent_name": talent.name,
            "status": talent.status.value,
            "evaluation_count": len(evaluations),
            "average_accuracy": sum(e.metrics["accuracy"] for e in evaluations.values()) / max(1, len(evaluations))
        },
        source="talent_integration",
        priority=MessagePriority.NORMAL
    )
    
    logger.info(f"Evaluation complete for talent: {talent.name} (new status: {talent.status.value})")
    
    return evaluations


async def _register_default_discovery_providers(self) -> None:
    """Register the default talent discovery providers."""
    from clarityos.prototype.talent_discovery import (
        discover_local_talents, discover_api_talents, 
        discover_plugin_talents, discover_cloud_talents
    )
    
    # Register all providers
    self.register_discovery_provider("local", discover_local_talents)
    self.register_discovery_provider("api", discover_api_talents)
    self.register_discovery_provider("plugin", discover_plugin_talents)
    self.register_discovery_provider("cloud", discover_cloud_talents)


async def _cancel_request(self, request_id: str) -> bool:
    """
    Cancel an active talent request.
    
    Args:
        request_id: ID of the request to cancel
        
    Returns:
        True if canceled, False if not found
    """
    request = self.active_requests.get(request_id)
    if not request:
        return False
    
    # Mark as canceled
    request.completed_at = time.time()
    request.success = False
    request.error = "Request canceled"
    
    # Remove from active requests
    del self.active_requests[request_id]
    
    logger.info(f"Canceled talent request: {request_id}")
    return True


def _generate_id(self, prefix: str) -> str:
    """
    Generate a unique ID with the given prefix.
    
    Args:
        prefix: Prefix for the ID
        
    Returns:
        Unique ID string
    """
    self._next_id_counter += 1
    return f"{prefix}_{self._next_id_counter}"


# Message handlers

async def _handle_talent_discover(self, message):
    """
    Handle talent discovery requests.
    
    Args:
        message: The message to handle
    """
    # Extract content
    content = message.content
    
    # Check if we should use a specific provider
    if "provider" in content:
        provider = content["provider"]
        if provider in self._discovery_providers:
            # Run discovery with just this provider
            try:
                talents = await self._discovery_providers[provider]()
                
                talent_ids = []
                for talent in talents:
                    if talent.id not in self.talents:
                        success = await self.register_talent(talent)
                        if success:
                            talent_ids.append(talent.id)
                
                # Send reply
                if message.reply_to:
                    await system_bus.publish(
                        message_type=f"{message.message_type}.reply",
                        content={
                            "success": True,
                            "discovered_count": len(talent_ids),
                            "talent_ids": talent_ids
                        },
                        source="talent_integration",
                        reply_to=message.source
                    )
            
            except Exception as e:
                # Send error reply
                if message.reply_to:
                    await system_bus.publish(
                        message_type=f"{message.message_type}.reply",
                        content={
                            "success": False,
                            "error": f"Error in discovery provider {provider}: {str(e)}"
                        },
                        source="talent_integration",
                        reply_to=message.source
                    )
            
        else:
            # Unknown provider
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "error": f"Unknown discovery provider: {provider}"
                    },
                    source="talent_integration",
                    reply_to=message.source
                )
    
    else:
        # Run discovery with all providers
        talent_ids = await self.discover_talents()
        
        # Send reply
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": True,
                    "discovered_count": len(talent_ids),
                    "talent_ids": talent_ids
                },
                source="talent_integration",
                reply_to=message.source
            )


async def _handle_talent_request(self, message):
    """
    Handle talent execution requests.
    
    Args:
        message: The message to handle
    """
    # Extract content
    content = message.content
    
    try:
        # Extract request details
        talent_id = content["talent_id"]
        capability_id = content["capability_id"]
        parameters = content.get("parameters", {})
        context = content.get("context", {})
        priority = content.get("priority", 1)
        
        # Execute the request
        success, result_msg, result = await self.request_talent(
            talent_id, capability_id, parameters, context, priority
        )
        
        # Send reply
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "message": result_msg,
                    "result": result
                },
                source="talent_integration",
                reply_to=message.source
            )
    
    except KeyError as e:
        # Missing required field
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": False,
                    "error": f"Missing required field: {str(e)}"
                },
                source="talent_integration",
                reply_to=message.source
            )
    
    except Exception as e:
        # Other error
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": False,
                    "error": f"Error handling talent request: {str(e)}"
                },
                source="talent_integration",
                reply_to=message.source
            )


async def _handle_talent_evaluate(self, message):
    """
    Handle talent evaluation requests.
    
    Args:
        message: The message to handle
    """
    # Extract content
    content = message.content
    
    try:
        # Extract request details
        talent_id = content["talent_id"]
        
        # Execute the evaluation
        evaluations = await self.evaluate_talent(talent_id)
        
        if evaluations is None:
            # Talent not found
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "error": f"Talent with ID {talent_id} not found"
                    },
                    source="talent_integration",
                    reply_to=message.source
                )
        else:
            # Convert evaluations to serializable format
            eval_dicts = {}
            for capability_id, evaluation in evaluations.items():
                eval_dicts[capability_id] = {
                    "benchmark_id": evaluation.benchmark_id,
                    "benchmark_name": evaluation.benchmark_name,
                    "metrics": evaluation.metrics,
                    "problems": evaluation.problems
                }
            
            # Send reply
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": True,
                        "talent_id": talent_id,
                        "evaluations": eval_dicts
                    },
                    source="talent_integration",
                    reply_to=message.source
                )
    
    except KeyError as e:
        # Missing required field
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": False,
                    "error": f"Missing required field: {str(e)}"
                },
                source="talent_integration",
                reply_to=message.source
            )
    
    except Exception as e:
        # Other error
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": False,
                    "error": f"Error handling talent evaluation: {str(e)}"
                },
                source="talent_integration",
                reply_to=message.source
            )
