"""
Learning Framework for ClarityOS

This module provides the core learning capabilities for ClarityOS,
enabling system-wide knowledge acquisition, adaptation, and improvement
through experience.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple, Callable, Union

from .message_bus import MessagePriority, system_bus

# Configure logging
logger = logging.getLogger(__name__)


class LearningDomain(Enum):
    """Domains for learning in the system."""
    SYSTEM = "system"            # System operations and optimization
    USER = "user"                # User preferences and behavior
    HARDWARE = "hardware"        # Hardware usage patterns
    APPLICATION = "application"  # Application behavior
    SECURITY = "security"        # Security patterns and threats
    NETWORK = "network"          # Network behavior and optimization
    INTENT = "intent"            # Natural language understanding


class LearningPriority(Enum):
    """Priority levels for learning tasks."""
    CRITICAL = 0  # Essential system behavior
    HIGH = 1      # Important patterns
    MEDIUM = 2    # Useful optimizations
    LOW = 3       # Nice-to-have improvements
    BACKGROUND = 4  # Long-term pattern analysis


class LearningStrategy(Enum):
    """Different learning strategies for different types of patterns."""
    SUPERVISED = "supervised"        # Learning from explicit feedback
    UNSUPERVISED = "unsupervised"    # Learning from patterns without labels
    REINFORCEMENT = "reinforcement"  # Learning from rewards/penalties
    FEDERATED = "federated"          # Learning across distributed systems
    TRANSFER = "transfer"            # Learning by applying knowledge from one domain to another
    ACTIVE = "active"                # Learning by actively seeking information


@dataclass
class LearningPattern:
    """Represents a learned pattern in the system."""
    id: str
    name: str
    domain: LearningDomain
    pattern_type: str
    confidence: float
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    usage_count: int = 0
    priority: LearningPriority = LearningPriority.MEDIUM


@dataclass
class LearningTask:
    """Represents a learning task to be executed."""
    id: str
    domain: LearningDomain
    task_type: str
    data: Dict[str, Any]
    priority: LearningPriority
    callback: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None


class LearningFramework:
    """
    Central learning system for ClarityOS.
    
    This class manages system-wide learning, including:
    - Pattern recognition and storage
    - Knowledge transfer between components
    - Continuous improvement of system behavior
    - Adaptation to user needs and preferences
    """
    
    def __init__(self):
        """Initialize the learning framework."""
        self.patterns: Dict[str, LearningPattern] = {}
        self.tasks: Dict[str, LearningTask] = {}
        self.knowledge_base: Dict[str, Dict[str, Any]] = {}
        self.strategy_handlers: Dict[LearningStrategy, Callable] = {}
        self.domain_handlers: Dict[LearningDomain, Callable] = {}
        self._next_pattern_id = 1
        self._next_task_id = 1
        self._initialized = False
        self._processing_task = None
        self._learning_task = None
        self._persistence_path = "data/learning"
        self._persistence_interval = 300  # 5 minutes
    
    async def initialize(self) -> bool:
        """Initialize the learning framework."""
        if self._initialized:
            logger.warning("Learning framework already initialized")
            return True
        
        logger.info("Initializing learning framework")
        
        try:
            # Import strategy and domain handlers
            from clarityos.learning.strategies import setup_strategy_handlers
            from clarityos.learning.domains import setup_domain_handlers
            
            # Set up strategy and domain handlers
            self.strategy_handlers = setup_strategy_handlers()
            self.domain_handlers = setup_domain_handlers()
            
            # Load existing knowledge if available
            await self._load_knowledge()
            
            # Subscribe to learning-related messages
            await self._subscribe_to_messages()
            
            # Start processing tasks
            self._processing_task = asyncio.create_task(self._process_learning_tasks())
            
            # Start background learning
            self._learning_task = asyncio.create_task(self._background_learning())
            
            # Start persistence task
            asyncio.create_task(self._persist_knowledge_periodically())
            
            self._initialized = True
            logger.info("Learning framework initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing learning framework: {str(e)}", exc_info=True)
            return False
    
    async def _load_knowledge(self):
        """Load existing knowledge from storage."""
        try:
            # Create storage directory if it doesn't exist
            os.makedirs(self._persistence_path, exist_ok=True)
            
            if os.path.exists(f"{self._persistence_path}/patterns.json"):
                with open(f"{self._persistence_path}/patterns.json", "r") as f:
                    pattern_data = json.load(f)
                    
                    for pattern_id, data in pattern_data.items():
                        self.patterns[pattern_id] = LearningPattern(
                            id=pattern_id,
                            name=data["name"],
                            domain=LearningDomain(data["domain"]),
                            pattern_type=data["pattern_type"],
                            confidence=data["confidence"],
                            data=data["data"],
                            metadata=data["metadata"],
                            created_at=data["created_at"],
                            last_updated=data["last_updated"],
                            usage_count=data["usage_count"],
                            priority=LearningPriority(data["priority"])
                        )
                    
                    logger.info(f"Loaded {len(self.patterns)} patterns from storage")
            
            if os.path.exists(f"{self._persistence_path}/knowledge_base.json"):
                with open(f"{self._persistence_path}/knowledge_base.json", "r") as f:
                    self.knowledge_base = json.load(f)
                    logger.info(f"Loaded knowledge base with {len(self.knowledge_base)} domains")
        
        except Exception as e:
            logger.error(f"Error loading knowledge: {str(e)}", exc_info=True)
            # Continue with empty knowledge - will be rebuilt over time
    
    async def _subscribe_to_messages(self):
        """Subscribe to learning-related messages on the system bus."""
        system_bus.subscribe(
            "learning.pattern.submit",
            self._handle_pattern_submit,
            "learning_framework"
        )
        
        system_bus.subscribe(
            "learning.pattern.query",
            self._handle_pattern_query,
            "learning_framework"
        )
        
        system_bus.subscribe(
            "learning.task.submit",
            self._handle_task_submit,
            "learning_framework"
        )
        
        system_bus.subscribe(
            "learning.feedback",
            self._handle_feedback,
            "learning_framework"
        )
        
        system_bus.subscribe(
            "learning.knowledge.query",
            self._handle_knowledge_query,
            "learning_framework"
        )
    
    async def _process_learning_tasks(self):
        """Process queued learning tasks."""
        try:
            while True:
                # Sort tasks by priority
                pending_tasks = [task for task in self.tasks.values() if task.status == "pending"]
                pending_tasks.sort(key=lambda t: t.priority.value)
                
                if pending_tasks:
                    # Process the highest priority task
                    task = pending_tasks[0]
                    await self._process_task(task)
                
                # Sleep to prevent CPU overuse
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logger.info("Learning task processor cancelled")
        except Exception as e:
            logger.error(f"Error in learning task processor: {str(e)}", exc_info=True)
    
    async def _process_task(self, task: LearningTask):
        """Process a single learning task."""
        try:
            # Update task status
            task.status = "processing"
            
            # Get appropriate handler for this domain
            domain_handler = self.domain_handlers.get(task.domain)
            if not domain_handler:
                logger.warning(f"No handler for learning domain: {task.domain}")
                task.status = "failed"
                task.result = {"error": f"No handler for domain: {task.domain}"}
                return
            
            # Process the task
            result = await domain_handler(task.data, task.task_type)
            
            # Update task status and result
            task.status = "completed"
            task.result = result
            
            # Send callback if requested
            if task.callback:
                await system_bus.publish(
                    message_type=task.callback,
                    content={
                        "task_id": task.id,
                        "result": result
                    },
                    source="learning_framework",
                    priority=MessagePriority.NORMAL
                )
            
        except Exception as e:
            logger.error(f"Error processing learning task {task.id}: {str(e)}", exc_info=True)
            task.status = "failed"
            task.result = {"error": str(e)}
            
            # Send failure callback if requested
            if task.callback:
                await system_bus.publish(
                    message_type=task.callback,
                    content={
                        "task_id": task.id,
                        "error": str(e)
                    },
                    source="learning_framework",
                    priority=MessagePriority.NORMAL
                )
    
    async def _background_learning(self):
        """Perform continuous background learning."""
        try:
            while True:
                # Wait for a period before doing background learning
                await asyncio.sleep(60)  # Every minute
                
                # Analyze recent system behavior
                await self._analyze_system_behavior()
                
                # Optimize based on patterns
                await self._apply_optimizations()
                
        except asyncio.CancelledError:
            logger.info("Background learning task cancelled")
        except Exception as e:
            logger.error(f"Error in background learning: {str(e)}", exc_info=True)
    
    async def _analyze_system_behavior(self):
        """Analyze recent system behavior for patterns."""
        # In a real implementation, this would analyze logs, metrics, etc.
        # For now, we'll just log that it happened
        logger.debug("Analyzing system behavior for patterns")
    
    async def _apply_optimizations(self):
        """Apply optimizations based on learned patterns."""
        # Apply optimizations based on learned patterns
        # For now, we'll just log that it happened
        logger.debug("Applying optimizations based on learned patterns")
    
    async def _persist_knowledge_periodically(self):
        """Periodically save knowledge to persistent storage."""
        try:
            while True:
                # Wait for the specified interval
                await asyncio.sleep(self._persistence_interval)
                
                # Save current knowledge
                await self._save_knowledge()
                
        except asyncio.CancelledError:
            logger.info("Knowledge persistence task cancelled")
            # One final save
            await self._save_knowledge()
        except Exception as e:
            logger.error(f"Error in knowledge persistence: {str(e)}", exc_info=True)
    
    async def _save_knowledge(self):
        """Save current knowledge to persistent storage."""
        try:
            # Ensure directory exists
            os.makedirs(self._persistence_path, exist_ok=True)
            
            # Save patterns
            pattern_data = {}
            for pattern_id, pattern in self.patterns.items():
                pattern_data[pattern_id] = {
                    "name": pattern.name,
                    "domain": pattern.domain.value,
                    "pattern_type": pattern.pattern_type,
                    "confidence": pattern.confidence,
                    "data": pattern.data,
                    "metadata": pattern.metadata,
                    "created_at": pattern.created_at,
                    "last_updated": pattern.last_updated,
                    "usage_count": pattern.usage_count,
                    "priority": pattern.priority.value
                }
            
            with open(f"{self._persistence_path}/patterns.json", "w") as f:
                json.dump(pattern_data, f, indent=2)
            
            # Save knowledge base
            with open(f"{self._persistence_path}/knowledge_base.json", "w") as f:
                json.dump(self.knowledge_base, f, indent=2)
                
            logger.info(f"Saved {len(self.patterns)} patterns and knowledge base to storage")
            
        except Exception as e:
            logger.error(f"Error saving knowledge: {str(e)}", exc_info=True)
    
    # Core API for other components to use
    
    async def submit_pattern(self, name: str, domain: LearningDomain, pattern_type: str,
                           data: Dict[str, Any], confidence: float = 0.5,
                           metadata: Dict[str, Any] = None) -> Tuple[bool, str, Optional[str]]:
        """Submit a new learning pattern to the system."""
        # Generate a unique ID
        pattern_id = f"pattern-{self._next_pattern_id}"
        self._next_pattern_id += 1
        
        # Create the pattern
        pattern = LearningPattern(
            id=pattern_id,
            name=name,
            domain=domain,
            pattern_type=pattern_type,
            confidence=confidence,
            data=data,
            metadata=metadata or {}
        )
        
        # Store the pattern
        self.patterns[pattern_id] = pattern
        
        logger.info(f"Registered pattern {name} (ID: {pattern_id}) for domain {domain.value}")
        
        # Publish pattern registered event
        await system_bus.publish(
            message_type="learning.pattern.registered",
            content={
                "pattern_id": pattern_id,
                "name": name,
                "domain": domain.value
            },
            source="learning_framework",
            priority=MessagePriority.NORMAL
        )
        
        return True, f"Pattern {name} registered with ID: {pattern_id}", pattern_id
    
    async def submit_task(self, domain: LearningDomain, task_type: str,
                       data: Dict[str, Any], priority: LearningPriority = LearningPriority.MEDIUM,
                       callback: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Submit a learning task for processing."""
        # Generate a unique ID
        task_id = f"task-{self._next_task_id}"
        self._next_task_id += 1
        
        # Create the task
        task = LearningTask(
            id=task_id,
            domain=domain,
            task_type=task_type,
            data=data,
            priority=priority,
            callback=callback
        )
        
        # Store the task
        self.tasks[task_id] = task
        
        logger.info(f"Submitted learning task (ID: {task_id}) for domain {domain.value}")
        
        return True, f"Task submitted with ID: {task_id}", task_id
    
    async def query_patterns(self, domain: Optional[LearningDomain] = None,
                           pattern_type: Optional[str] = None,
                           min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """Query for patterns matching specified criteria."""
        result = []
        
        for pattern in self.patterns.values():
            # Apply filters
            if domain and pattern.domain != domain:
                continue
                
            if pattern_type and pattern.pattern_type != pattern_type:
                continue
                
            if pattern.confidence < min_confidence:
                continue
                
            # Add to results
            result.append({
                "id": pattern.id,
                "name": pattern.name,
                "domain": pattern.domain.value,
                "pattern_type": pattern.pattern_type,
                "confidence": pattern.confidence
            })
        
        return result
    
    async def get_knowledge(self, domain: str, key: Optional[str] = None) -> Any:
        """Get knowledge from the knowledge base."""
        if domain not in self.knowledge_base:
            return None
            
        if key:
            return self.knowledge_base[domain].get(key)
        
        return self.knowledge_base[domain]
    
    async def set_knowledge(self, domain: str, key: str, value: Any) -> bool:
        """Set knowledge in the knowledge base."""
        if domain not in self.knowledge_base:
            self.knowledge_base[domain] = {}
            
        self.knowledge_base[domain][key] = value
        
        # Save immediately for important updates
        if domain in ("system", "security"):
            await self._save_knowledge()
            
        return True
    
    async def provide_feedback(self, pattern_id: str, is_positive: bool,
                            confidence_adjustment: float = 0.1,
                            details: Optional[Dict[str, Any]] = None) -> bool:
        """Provide feedback on a pattern to adjust its confidence."""
        if pattern_id not in self.patterns:
            logger.warning(f"Pattern {pattern_id} not found for feedback")
            return False
            
        pattern = self.patterns[pattern_id]
        
        # Adjust confidence based on feedback
        if is_positive:
            pattern.confidence = min(1.0, pattern.confidence + confidence_adjustment)
        else:
            pattern.confidence = max(0.0, pattern.confidence - confidence_adjustment)
            
        # Update pattern
        pattern.last_updated = time.time()
        pattern.usage_count += 1
        
        if details:
            # Merge with existing metadata
            if "feedback" not in pattern.metadata:
                pattern.metadata["feedback"] = []
                
            feedback_entry = {
                "timestamp": time.time(),
                "is_positive": is_positive,
                "details": details
            }
            
            pattern.metadata["feedback"].append(feedback_entry)
            
        logger.info(f"Updated pattern {pattern_id} confidence to {pattern.confidence:.2f} based on feedback")
        
        return True
    
    # Message handlers
    
    async def _handle_pattern_submit(self, message):
        """Handle pattern submission messages."""
        content = message.content
        
        success, message_text, pattern_id = await self.submit_pattern(
            name=content["name"],
            domain=LearningDomain(content["domain"]),
            pattern_type=content["pattern_type"],
            data=content["data"],
            confidence=content.get("confidence", 0.5),
            metadata=content.get("metadata")
        )
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "message": message_text,
                    "pattern_id": pattern_id
                },
                source="learning_framework",
                reply_to=message.source
            )
    
    async def _handle_pattern_query(self, message):
        """Handle pattern query messages."""
        content = message.content
        
        domain = None
        if "domain" in content:
            domain = LearningDomain(content["domain"])
            
        patterns = await self.query_patterns(
            domain=domain,
            pattern_type=content.get("pattern_type"),
            min_confidence=content.get("min_confidence", 0.0)
        )
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "patterns": patterns,
                    "count": len(patterns)
                },
                source="learning_framework",
                reply_to=message.source
            )
    
    async def _handle_task_submit(self, message):
        """Handle task submission messages."""
        content = message.content
        
        success, message_text, task_id = await self.submit_task(
            domain=LearningDomain(content["domain"]),
            task_type=content["task_type"],
            data=content["data"],
            priority=LearningPriority(content.get("priority", LearningPriority.MEDIUM.value)),
            callback=content.get("callback")
        )
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "message": message_text,
                    "task_id": task_id
                },
                source="learning_framework",
                reply_to=message.source
            )
    
    async def _handle_feedback(self, message):
        """Handle pattern feedback messages."""
        content = message.content
        
        success = await self.provide_feedback(
            pattern_id=content["pattern_id"],
            is_positive=content["is_positive"],
            confidence_adjustment=content.get("confidence_adjustment", 0.1),
            details=content.get("details")
        )
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "pattern_id": content["pattern_id"]
                },
                source="learning_framework",
                reply_to=message.source
            )
    
    async def _handle_knowledge_query(self, message):
        """Handle knowledge query messages."""
        content = message.content
        
        domain = content["domain"]
        key = content.get("key")
        
        knowledge = await self.get_knowledge(domain, key)
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "domain": domain,
                    "key": key,
                    "knowledge": knowledge,
                    "found": knowledge is not None
                },
                source="learning_framework",
                reply_to=message.source
            )
    
    async def shutdown(self):
        """Shut down the learning framework."""
        logger.info("Shutting down learning framework")
        
        # Cancel processing task
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        # Cancel learning task
        if self._learning_task:
            self._learning_task.cancel()
            try:
                await self._learning_task
            except asyncio.CancelledError:
                pass
        
        # Final knowledge save
        await self._save_knowledge()
        
        self._initialized = False
        logger.info("Learning framework shutdown complete")


# Singleton instance
learning_framework = LearningFramework()
