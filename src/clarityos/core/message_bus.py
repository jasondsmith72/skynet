"""
ClarityOS Message Bus

This module provides a system-wide asynchronous message bus for communication
between different components of ClarityOS. It uses a topic-based
publish-subscribe model.
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Message:
    """Represents a message on the bus."""
    message_type: str
    content: Any
    source: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None


class MessageBus:
    """
    Asynchronous message bus for ClarityOS.

    This class implements a topic-based publish-subscribe system
    that allows different components to communicate asynchronously.
    """

    def __init__(self):
        self.subscribers: Dict[str, Dict[str, Callable[[Message], Coroutine]]] = defaultdict(dict)
        self.queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    def start(self):
        """Start the message bus worker."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Message bus started")

    def stop(self):
        """Stop the message bus worker."""
        if self._running:
            self._running = False
            if self._worker_task:
                self._worker_task.cancel()
                self._worker_task = None
            logger.info("Message bus stopped")

    async def _worker(self):
        """Main worker task that processes messages from the queue."""
        while self._running:
            try:
                message = await self.queue.get()
                await self._dispatch(message)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message bus worker: {e}")

    async def publish(
        self,
        message_type: str,
        content: Any,
        source: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        reply_to: Optional[str] = None
    ) -> Message:
        """
        Publish a message to the bus.

        Args:
            message_type: The topic of the message (e.g., "system.cpu.usage")
            content: The message payload
            source: The component that sent the message
            priority: The priority of the message
            reply_to: The ID of the message this is a reply to

        Returns:
            The created message object
        """
        message = Message(
            message_type=message_type,
            content=content,
            source=source,
            priority=priority,
            reply_to=reply_to
        )
        await self.queue.put(message)
        return message

    async def subscribe(
        self,
        message_type: str,
        callback: Callable[[Message], Coroutine],
        subscriber_id: str
    ) -> bool:
        """
        Subscribe to a message topic.

        Args:
            message_type: The topic to subscribe to (can include wildcards)
            callback: The async function to call when a message is received
            subscriber_id: A unique identifier for the subscriber

        Returns:
            True if subscription was successful, False otherwise
        """
        if not asyncio.iscoroutinefunction(callback):
            logger.error(f"Subscriber callback for '{message_type}' must be a coroutine")
            return False

        self.subscribers[message_type][subscriber_id] = callback
        logger.info(f"Subscriber '{subscriber_id}' subscribed to '{message_type}'")
        return True

    async def unsubscribe(self, message_type: str, subscriber_id: str) -> bool:
        """
        Unsubscribe from a message topic.

        Args:
            message_type: The topic to unsubscribe from
            subscriber_id: The ID of the subscriber to remove

        Returns:
            True if successful, False if subscriber was not found
        """
        if message_type in self.subscribers and subscriber_id in self.subscribers[message_type]:
            del self.subscribers[message_type][subscriber_id]
            logger.info(f"Subscriber '{subscriber_id}' unsubscribed from '{message_type}'")
            return True
        return False

    async def _dispatch(self, message: Message):
        """Dispatch a message to all matching subscribers."""

        # Keep track of dispatched callbacks to avoid duplicates
        dispatched_callbacks = set()

        for pattern, pattern_subscribers in self.subscribers.items():
            if self._topic_matches(message.message_type, pattern):
                for subscriber_id, callback in pattern_subscribers.items():
                    if callback not in dispatched_callbacks:
                        try:
                            await callback(message)
                            dispatched_callbacks.add(callback)
                        except Exception as e:
                            logger.error(
                                f"Error executing callback for subscriber '{subscriber_id}' "
                                f"on topic '{message.message_type}': {e}"
                            )

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """
        Check if a topic matches a pattern with wildcards.

        Wildcards:
        - '*': Matches any sequence of characters within a single topic level
        - '#': Matches any number of topic levels (including zero)
        
        Examples:
        - 'system.cpu.*' matches 'system.cpu.usage' but not 'system.cpu.core.0.usage'
        - 'system.#' matches 'system.cpu.usage' and 'system.memory.free'
        
        Args:
            topic: Topic to check
            pattern: Pattern to match against
        
        Returns:
            True if the topic matches the pattern, False otherwise
        """
        # Split into parts
        topic_parts = topic.split('.')
        pattern_parts = pattern.split('.')
        
        # Simple check for exact match
        if pattern == topic:
            return True
        
        i, j = 0, 0
        while i < len(topic_parts) and j < len(pattern_parts):
            if pattern_parts[j] == '#':
                # '#' matches any number of levels, including zero
                return True
            elif pattern_parts[j] == '*':
                # '*' matches exactly one level
                i += 1
                j += 1
            elif pattern_parts[j] == topic_parts[i]:
                # Exact match for this level
                i += 1
                j += 1
            else:
                # No match
                return False
        
        # If we've consumed all of both topic and pattern, it's a match
        return i == len(topic_parts) and j == len(pattern_parts)


# Singleton instance of the message bus
system_bus = MessageBus()