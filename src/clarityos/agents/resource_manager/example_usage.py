#!/usr/bin/env python3
"""
Example usage of the ResourceManagerAgent.

This script demonstrates how to use the ResourceManagerAgent in a ClarityOS environment,
including initialization, resource requests, and monitoring resource usage.
"""

import asyncio
import logging
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ResourceManagerExample")

# Import required components
from clarityos.core.message_bus import MessageBus
from clarityos.core.resource_types import ResourceType, ResourceRequest
from clarityos.core.priority import Priority
from clarityos.agents.resource_manager.resource_manager_agent import ResourceManagerAgent

# Example component that requests resources
class ExampleComponent:
    """Example component that requests and uses resources."""
    
    def __init__(self, component_id: str, message_bus: MessageBus):
        """Initialize the example component.
        
        Args:
            component_id: Unique identifier for this component
            message_bus: Message bus for communication
        """
        self.component_id = component_id
        self.message_bus = message_bus
        self.logger = logging.getLogger(f"Component:{component_id}")
        self.resources_allocated = {}
    
    async def start(self):
        """Start the component."""
        self.logger.info(f"Starting component {self.component_id}")
        
        # Notify system that component has started
        await self.message_bus.publish("system.component.started", {
            "component_id": self.component_id,
            "metadata": {
                "component_type": "example"
            }
        })
        
        # Subscribe to resource allocation messages
        await self.message_bus.subscribe(
            "system.resource.allocation",
            self._handle_resource_allocation,
            filter_func=lambda msg: msg.get("component_id") == self.component_id
        )
    
    async def stop(self):
        """Stop the component."""
        self.logger.info(f"Stopping component {self.component_id}")
        
        # Release all resources
        for resource_type in list(self.resources_allocated.keys()):
            await self.release_resource(resource_type)
        
        # Notify system that component has stopped
        await self.message_bus.publish("system.component.stopped", {
            "component_id": self.component_id
        })
    
    async def request_resource(self, resource_type: ResourceType, amount: float):
        """Request allocation of a resource.
        
        Args:
            resource_type: Type of resource to request
            amount: Amount of resource requested
        
        Returns:
            Allocated amount of resource
        """
        self.logger.info(f"Requesting {amount} of {resource_type.name}")
        
        # Create the request message
        request_message = {
            "component_id": self.component_id,
            "resource_type": resource_type.name,
            "requested_amount": amount,
            "priority": Priority.NORMAL.name,
            "reason": "Example usage"
        }
        
        # Send the request
        response = await self.message_bus.request("system.resource.request", request_message, timeout=5.0)
        
        # Check if request was successful
        if response.get("success", False):
            allocated_amount = response.get("allocated_amount", 0.0)
            self.resources_allocated[resource_type] = allocated_amount
            self.logger.info(f"Resource {resource_type.name} allocated: {allocated_amount}")
            return allocated_amount
        else:
            self.logger.warning(f"Resource request failed: {response.get('message', 'Unknown error')}")
            return 0.0
    
    async def release_resource(self, resource_type: ResourceType):
        """Release a previously allocated resource.
        
        Args:
            resource_type: Type of resource to release
        """
        if resource_type in self.resources_allocated:
            self.logger.info(f"Releasing resource {resource_type.name}")
            
            # Create the release message
            release_message = {
                "component_id": self.component_id,
                "resource_type": resource_type.name
            }
            
            # Send the release request
            response = await self.message_bus.request(f"system.resource.release", release_message, timeout=5.0)
            
            # Check if release was successful
            if response.get("success", False):
                del self.resources_allocated[resource_type]
                self.logger.info(f"Resource {resource_type.name} released successfully")
            else:
                self.logger.warning(f"Resource release failed: {response.get('message', 'Unknown error')}")
    
    async def _handle_resource_allocation(self, message: Dict[str, Any]):
        """Handle resource allocation messages.
        
        Args:
            message: Resource allocation message
        """
        resource_type_name = message.get("resource_type")
        allocation = message.get("allocation", 0.0)
        previous = message.get("previous_allocation", 0.0)
        
        if resource_type_name:
            try:
                resource_type = ResourceType[resource_type_name]
                self.resources_allocated[resource_type] = allocation
                self.logger.info(f"Resource allocation updated: {resource_type_name} = {previous} -> {allocation}")
            except KeyError:
                self.logger.warning(f"Unknown resource type: {resource_type_name}")

# Main example function
async def main():
    """Run the resource manager example."""
    # Create message bus
    message_bus = MessageBus()
    await message_bus.start()
    
    try:
        # Create and initialize resource manager
        resource_manager = ResourceManagerAgent(message_bus)
        await resource_manager.initialize()
        
        # Create example components
        component1 = ExampleComponent("example1", message_bus)
        component2 = ExampleComponent("example2", message_bus)
        
        # Start components
        await component1.start()
        await component2.start()
        
        # Request resources for component 1
        await component1.request_resource(ResourceType.CPU, 2.0)  # Request 2 CPU cores
        await component1.request_resource(ResourceType.MEMORY, 1024.0)  # Request 1 GB memory
        
        # Request resources for component 2
        await component2.request_resource(ResourceType.CPU, 3.0)  # Request 3 CPU cores
        await component2.request_resource(ResourceType.MEMORY, 2048.0)  # Request 2 GB memory
        
        # Wait a bit to simulate system running
        logger.info("System running with allocated resources")
        await asyncio.sleep(5)
        
        # Get resource usage information
        response = await resource_manager.mcp_server.get_resource_usage()
        logger.info(f"Current resource usage: {response}")
        
        # Release some resources from component 1
        await component1.release_resource(ResourceType.CPU)
        
        # Wait a bit to see the effect
        logger.info("After releasing some resources")
        await asyncio.sleep(2)
        
        # Get updated resource usage information
        response = await resource_manager.mcp_server.get_resource_usage()
        logger.info(f"Updated resource usage: {response}")
        
        # Request more resources than available for component 2
        logger.info("Requesting more resources than available")
        await component2.request_resource(ResourceType.CPU, 10.0)  # Request 10 CPU cores (should be limited)
        
        # Stop components
        await component1.stop()
        await component2.stop()
        
    finally:
        # Shutdown resource manager
        await resource_manager.shutdown()
        
        # Stop message bus
        await message_bus.stop()

# Run the example
if __name__ == "__main__":
    asyncio.run(main())