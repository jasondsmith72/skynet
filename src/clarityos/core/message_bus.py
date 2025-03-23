"""
Message Bus for ClarityOS

This module implements the central message bus that allows all system
components to communicate. It features priority-based messaging, a
subscription model, and message transformation capabilities.
"""

import asyncio
import json
import logging
import time
import uuid
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Set, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessagePriority(IntEnum):
    """Message priority levels for the bus."""
    CRITICAL = 0  # System critical (security threats, critical resource issues)
    HIGH = 1      # Important system operations (security warnings, resource allocation)
    NORMAL = 2    # Standard operations
    LOW = 3       # Background tasks
    LOWEST = 4    # Logging, metrics


class Message:
    """Represents a message on the bus."""
    
    def __init__(
        self,
        message_type: str,
        content: Any,
        source: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid.uuid4())
        self.timestamp = time.time()
        self.message_type = message_type
        self.content = content
        self.source = source
        self.priority = priority
        self.correlation_id = correlation_id or self.id
        self.reply_to = reply_to
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
            "content": self.content,
            "source": self.source,
            "priority": int(self.priority),
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a message from a dictionary."""
        msg = cls(
            message_type=data["message_type"],
            content=data["content"],
            source=data["source"],
            priority=MessagePriority(data["priority"]),
            correlation_id=data["correlation_id"],
            reply_to=data.get("reply_to"),
            metadata=data.get("metadata", {})
        )
        msg.id = data["id"]
        msg.timestamp = data["timestamp"]
        return msg
    
    def create_reply(self, content: Any) -> 'Message':
        """Create a reply to this message."""
        return Message(
            message_type=f"{self.message_type}.reply",
            content=content,
            source=self.reply_to or "system",
            priority=self.priority,
            correlation_id=self.correlation_id,
            reply_to=self.source
        )


MessageHandler = Callable[[Message], Union[None, Any, asyncio.Future]]


class SystemMessageBus:
    """
    Central message bus for ClarityOS.
    
    This class implements a priority-based, publish-subscribe message bus
    that serves as the primary communication mechanism for all system
    components.
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, Dict[str, MessageHandler]] = {}
        self._wildcard_subscriptions: Dict[str, MessageHandler] = {}
        self._priority_queues: Dict[MessagePriority, asyncio.Queue] = {
            priority: asyncio.Queue() for priority in MessagePriority
        }
        self._worker_tasks: List[asyncio.Task] = []
        self._message_history: List[Message] = []
        self._max_history_size = 1000
        self._running = False
        self._lock = asyncio.Lock()
        
    async def start(self) -> None:
        """Start the message bus."""
        async with self._lock:
            if self._running:
                return
            
            self._running = True
            
            # Create worker tasks for each priority level
            for priority in MessagePriority:
                for _ in range(3 if priority <= MessagePriority.HIGH else 1):  # More workers for high priority
                    task = asyncio.create_task(self._message_worker(priority))
                    self._worker_tasks.append(task)
            
            logger.info("System message bus started")
    
    async def stop(self) -> None:
        """Stop the message bus."""
        async with self._lock:
            if not self._running:
                return
            
            self._running = False
            
            # Cancel all worker tasks
            for task in self._worker_tasks:
                task.cancel()
            
            # Wait for tasks to finish
            if self._worker_tasks:
                await asyncio.gather(*self._worker_tasks, return_exceptions=True)
            
            self._worker_tasks.clear()
            logger.info("System message bus stopped")
    
    async def _message_worker(self, priority: MessagePriority) -> None:
        """Worker task for processing messages of a specific priority."""
        queue = self._priority_queues[priority]
        
        while self._running:
            try:
                message = await queue.get()
                await self._process_message(message)
                queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
    
    async def _process_message(self, message: Message) -> None:
        """Process a single message by delivering it to subscribers."""
        # Store in history
        self._store_in_history(message)
        
        # Get handlers for this message type
        handlers = []
        
        # Add specific handlers for this message type
        if message.message_type in self._subscriptions:
            handlers.extend(self._subscriptions[message.message_type].values())
        
        # Add wildcard handlers
        handlers.extend(self._wildcard_subscriptions.values())
        
        # No handlers for this message
        if not handlers:
            logger.debug(f"No handlers for message type: {message.message_type}")
            return
        
        # Call all handlers
        for handler in handlers:
            try:
                result = handler(message)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in message handler: {str(e)}", exc_info=True)
    
    def _store_in_history(self, message: Message) -> None:
        """Store message in history, maintaining maximum size."""
        self._message_history.append(message)
        
        # Trim history if needed
        if len(self._message_history) > self._max_history_size:
            self._message_history = self._message_history[-self._max_history_size:]
    
    async def publish(
        self,
        message_type: str,
        content: Any,
        source: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Publish a message to the bus.
        
        Args:
            message_type: Type of message being published
            content: Message content (must be serializable)
            source: Component that generated the message
            priority: Message priority level
            correlation_id: ID for correlating related messages
            reply_to: Where to send replies
            metadata: Additional message metadata
            
        Returns:
            The created Message object
        """
        message = Message(
            message_type=message_type,
            content=content,
            source=source,
            priority=priority,
            correlation_id=correlation_id,
            reply_to=reply_to,
            metadata=metadata
        )
        
        # Add to appropriate queue
        await self._priority_queues[priority].put(message)
        
        return message
    
    def subscribe(
        self,
        message_type: str,
        handler: MessageHandler,
        subscriber_id: Optional[str] = None
    ) -> str:
        """
        Subscribe to a specific message type.
        
        Args:
            message_type: Message type to subscribe to, or "*" for all messages
            handler: Function to call when a matching message is received
            subscriber_id: Optional ID for this subscription
            
        Returns:
            Subscription ID
        """
        sub_id = subscriber_id or str(uuid.uuid4())
        
        if message_type == "*":
            self._wildcard_subscriptions[sub_id] = handler
        else:
            if message_type not in self._subscriptions:
                self._subscriptions[message_type] = {}
            
            self._subscriptions[message_type][sub_id] = handler
        
        return sub_id
    
    def unsubscribe(self, message_type: str, subscriber_id: str) -> bool:
        """
        Unsubscribe from a message type.
        
        Args:
            message_type: Message type to unsubscribe from, or "*" for all messages
            subscriber_id: Subscription ID to remove
            
        Returns:
            True if subscription was found and removed, False otherwise
        """
        if message_type == "*":
            if subscriber_id in self._wildcard_subscriptions:
                del self._wildcard_subscriptions[subscriber_id]
                return True
        elif message_type in self._subscriptions:
            if subscriber_id in self._subscriptions[message_type]:
                del self._subscriptions[message_type][subscriber_id]
                
                # Clean up empty message type dictionary
                if not self._subscriptions[message_type]:
                    del self._subscriptions[message_type]
                
                return True
        
        return False
    
    def query_history(
        self,
        message_type: Optional[str] = None,
        source: Optional[str] = None,
        time_from: Optional[float] = None,
        time_to: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Query message history.
        
        Args:
            message_type: Filter by message type
            source: Filter by source
            time_from: Filter by time (from)
            time_to: Filter by time (to)
            limit: Limit the number of results
            
        Returns:
            List of matching messages
        """
        results = self._message_history.copy()
        
        # Apply filters
        if message_type:
            results = [m for m in results if m.message_type == message_type]
        
        if source:
            results = [m for m in results if m.source == source]
        
        if time_from:
            results = [m for m in results if m.timestamp >= time_from]
        
        if time_to:
            results = [m for m in results if m.timestamp <= time_to]
        
        # Apply limit and return most recent messages first
        results.sort(key=lambda m: m.timestamp, reverse=True)
        
        if limit:
            results = results[:limit]
        
        return results
    
    def get_active_subscriptions(self) -> Dict[str, List[str]]:
        """
        Get active subscriptions.
        
        Returns:
            Dictionary mapping message types to lists of subscriber IDs
        """
        result = {}
        
        # Add wildcards
        if self._wildcard_subscriptions:
            result["*"] = list(self._wildcard_subscriptions.keys())
        
        # Add specific subscriptions
        for message_type, subscribers in self._subscriptions.items():
            result[message_type] = list(subscribers.keys())
        
        return result
    
    async def request_response(
        self,
        message_type: str,
        content: Any,
        source: str,
        timeout: float = 5.0,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Optional[Message]:
        """
        Send a message and wait for a response.
        
        Args:
            message_type: Type of message to send
            content: Message content
            source: Message source
            timeout: How long to wait for a response
            priority: Message priority
            
        Returns:
            Response message, or None if timeout exceeded
        """
        response_future = asyncio.Future()
        response_id = str(uuid.uuid4())
        
        # Handler for the response
        def response_handler(message: Message):
            if not response_future.done():
                response_future.set_result(message)
        
        # Subscribe to responses
        self.subscribe(f"{message_type}.reply", response_handler, response_id)
        
        try:
            # Send the request
            await self.publish(
                message_type=message_type,
                content=content,
                source=source,
                priority=priority,
                reply_to=response_id
            )
            
            # Wait for response
            return await asyncio.wait_for(response_future, timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response to {message_type}")
            return None
        finally:
            # Clean up subscription
            self.unsubscribe(f"{message_type}.reply", response_id)


# Create a singleton instance
# This provides a global message bus for the entire system
system_bus = SystemMessageBus()
