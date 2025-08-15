#!/usr/bin/env python3
"""
Base class for all agents in ClarityOS.

This module provides the foundational class that all ClarityOS agents inherit from,
establishing common interfaces and behaviors for the agent system.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Awaitable

from .message_bus import MessageBus

class AgentBase(ABC):
    """Base class for all agents in ClarityOS."""
    
    def __init__(self, agent_id: str, message_bus: MessageBus):
        """Initialize the agent with its ID and a message bus connection.
        
        Args:
            agent_id: Unique identifier for this agent
            message_bus: Message bus for inter-agent communication
        """
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.logger = logging.getLogger(f"Agent:{agent_id}")
        
        # State tracking
        self.initialized = False
        self.subscriptions = []
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent.
        
        This method should be overridden by derived classes to perform
        any necessary setup, such as subscribing to message topics and
        initializing resources.
        
        Returns:
            None
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the agent gracefully.
        
        This method should be overridden by derived classes to perform
        any necessary cleanup, such as unsubscribing from message topics
        and releasing resources.
        
        Returns:
            None
        """
        pass
    
    async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Subscribe to a message topic with a handler function.
        
        Args:
            topic: Message topic to subscribe to
            handler: Async callback function to handle messages
        
        Returns:
            None
        """
        await self.message_bus.subscribe(topic, handler)
        self.subscriptions.append((topic, handler))
        self.logger.debug(f"Subscribed to topic: {topic}")
    
    async def unsubscribe_all(self) -> None:
        """Unsubscribe from all previously subscribed topics.
        
        Returns:
            None
        """
        for topic, handler in self.subscriptions:
            await self.message_bus.unsubscribe(topic, handler)
            self.logger.debug(f"Unsubscribed from topic: {topic}")
        
        self.subscriptions = []
    
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish a message to a topic.
        
        Args:
            topic: Topic to publish the message to
            message: Message data as a dictionary
        
        Returns:
            None
        """
        # Add agent_id to the message metadata
        if 'metadata' not in message:
            message['metadata'] = {}
        
        message['metadata']['source_agent'] = self.agent_id
        message['metadata']['timestamp'] = asyncio.get_event_loop().time()
        
        await self.message_bus.publish(topic, message)
        self.logger.debug(f"Published message to topic: {topic}")
    
    async def request(self, topic: str, message: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
        """Send a request and wait for a response.
        
        Args:
            topic: Topic to send the request to
            message: Request message data
            timeout: Timeout in seconds
        
        Returns:
            Response message
        
        Raises:
            asyncio.TimeoutError: If no response is received within the timeout
        """
        return await self.message_bus.request(topic, message, timeout)
    
    async def run_periodic(self, interval: float, task: Callable[[], Awaitable[None]]) -> None:
        """Run a task periodically.
        
        Args:
            interval: Interval in seconds between task executions
            task: Async task function to run
        
        Returns:
            None
        """
        while True:
            try:
                await task()
            except Exception as e:
                self.logger.error(f"Error in periodic task: {e}")
            
            await asyncio.sleep(interval)