#!/usr/bin/env python3
"""
ResourceManagerAgent for ClarityOS

This agent is responsible for monitoring and optimizing system resources,
ensuring efficient allocation and preventing resource contention across
the system.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from fastmcp import FastMCP
from ...core.message_bus import MessageBus
from ...core.agent_base import AgentBase
from ...core.priority import Priority
from ...core.resource_types import ResourceType, ResourceAllocation, ResourceRequest
from ...core.system_monitor import SystemMonitor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ResourceManagerAgent')

@dataclass
class ResourceUsageHistory:
    """Records historical resource usage for a component."""
    component_id: str
    resource_type: ResourceType
    usage_samples: List[Tuple[float, float]] = field(default_factory=list)  # (timestamp, usage_percentage)
    allocation: float = 0.0  # Current allocation

    def add_sample(self, usage: float):
        """Add a usage sample with current timestamp."""
        self.usage_samples.append((time.time(), usage))
        # Keep only the last 100 samples to limit memory usage
        if len(self.usage_samples) > 100:
            self.usage_samples = self.usage_samples[-100:]

    def get_average_usage(self, window_seconds: float = 60.0) -> float:
        """Calculate average usage over the specified time window."""
        if not self.usage_samples:
            return 0.0
            
        now = time.time()
        recent_samples = [u for t, u in self.usage_samples if now - t <= window_seconds]
        if not recent_samples:
            return 0.0
            
        return sum(recent_samples) / len(recent_samples)
    
    def get_peak_usage(self, window_seconds: float = 60.0) -> float:
        """Calculate peak usage over the specified time window."""
        if not self.usage_samples:
            return 0.0
            
        now = time.time()
        recent_samples = [u for t, u in self.usage_samples if now - t <= window_seconds]
        if not recent_samples:
            return 0.0
            
        return max(recent_samples)
        
    def get_trend(self, window_seconds: float = 300.0) -> float:
        """Calculate usage trend (positive means increasing)."""
        if len(self.usage_samples) < 2:
            return 0.0
            
        now = time.time()
        recent_samples = [(t, u) for t, u in self.usage_samples if now - t <= window_seconds]
        if len(recent_samples) < 2:
            return 0.0
            
        # Simple linear regression to find trend
        times, usages = zip(*recent_samples)
        times = [t - min(times) for t in times]  # Normalize times
        
        n = len(times)
        sum_x = sum(times)
        sum_y = sum(usages)
        sum_xy = sum(x * y for x, y in zip(times, usages))
        sum_x2 = sum(x * x for x in times)
        
        # Calculate slope of best fit line
        try:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            return slope
        except ZeroDivisionError:
            return 0.0


class ResourceManagerAgent(AgentBase):
    """
    ResourceManagerAgent monitors system resources and optimizes allocations
    based on system load, application priorities, and predicted needs.
    """
    
    def __init__(self, message_bus: MessageBus):
        """Initialize the resource manager agent."""
        super().__init__("resource_manager", message_bus)
        
        # Initialize resource tracking
        self.resources_by_type: Dict[ResourceType, float] = {}  # Total resources available by type
        self.component_resources: Dict[str, Dict[ResourceType, ResourceUsageHistory]] = {}
        
        # Initialize system monitoring
        self.system_monitor = SystemMonitor()
        
        # Set up MCP server for API access
        self.mcp_server = FastMCP("resource-manager")
        self._register_mcp_tools()
        
        # Flag to control agent running state
        self.running = False

    def _register_mcp_tools(self):
        """Register MCP tools for external interaction with this agent."""
        
        @self.mcp_server.tool()
        async def allocate_resources(component_id: str, resource_type: str, amount: float) -> str:
            """
            Request allocation of resources for a component.
            
            Args:
                component_id: Identifier for the requesting component
                resource_type: Type of resource requested (CPU, MEMORY, etc.)
                amount: Amount of resource requested (percentage of total)
            """
            try:
                rt = ResourceType[resource_type.upper()]
                result = await self.handle_resource_request(
                    ResourceRequest(
                        component_id=component_id,
                        resource_type=rt,
                        requested_amount=amount,
                        priority=Priority.NORMAL
                    )
                )
                return json.dumps({"success": True, "allocated": result.allocated_amount})
            except Exception as e:
                logger.error(f"Error in allocate_resources: {e}")
                return json.dumps({"success": False, "error": str(e)})
        
        @self.mcp_server.tool()
        async def get_resource_usage(component_id: str = None) -> str:
            """
            Get current resource usage information.
            
            Args:
                component_id: Optional component to get resources for. If None, returns all
            """
            try:
                if component_id:
                    if component_id in self.component_resources:
                        result = {
                            rt.name: {
                                "allocation": history.allocation,
                                "current_usage": history.get_average_usage(10),
                                "peak_usage": history.get_peak_usage(60),
                                "trend": history.get_trend(300)
                            }
                            for rt, history in self.component_resources[component_id].items()
                        }
                    else:
                        result = {"error": f"Component {component_id} not found"}
                else:
                    result = {
                        "system_total": {rt.name: total for rt, total in self.resources_by_type.items()},
                        "components": {
                            comp_id: {
                                rt.name: {
                                    "allocation": history.allocation,
                                    "current_usage": history.get_average_usage(10),
                                }
                                for rt, history in resources.items()
                            }
                            for comp_id, resources in self.component_resources.items()
                        }
                    }
                return json.dumps(result)
            except Exception as e:
                logger.error(f"Error in get_resource_usage: {e}")
                return json.dumps({"success": False, "error": str(e)})
    
    async def initialize(self):
        """Initialize the agent and discover available system resources."""
        logger.info("Initializing ResourceManagerAgent")
        
        # Discover available resources
        await self._discover_resources()
        
        # Subscribe to resource-related messages
        await self.message_bus.subscribe("system.resource.request", self._handle_resource_request)
        await self.message_bus.subscribe("system.resource.release", self._handle_resource_release)
        await self.message_bus.subscribe("system.component.started", self._handle_component_started)
        await self.message_bus.subscribe("system.component.stopped", self._handle_component_stopped)
        
        # Start monitoring thread
        self.running = True
        asyncio.create_task(self._monitoring_task())
        
        logger.info(f"ResourceManagerAgent initialized with resources: {self.resources_by_type}")
        
    async def shutdown(self):
        """Shutdown the agent gracefully."""
        logger.info("Shutting down ResourceManagerAgent")
        self.running = False
        # Unsubscribe from topics
        await self.message_bus.unsubscribe("system.resource.request", self._handle_resource_request)
        await self.message_bus.unsubscribe("system.resource.release", self._handle_resource_release)
        await self.message_bus.unsubscribe("system.component.started", self._handle_component_started)
        await self.message_bus.unsubscribe("system.component.stopped", self._handle_component_stopped)
    
    async def _discover_resources(self):
        """Discover available system resources."""
        system_info = self.system_monitor.get_system_info()
        
        # Map system info to our resource types
        self.resources_by_type[ResourceType.CPU] = system_info.cpu_count
        self.resources_by_type[ResourceType.MEMORY] = system_info.total_memory / (1024 * 1024)  # Convert to MB
        self.resources_by_type[ResourceType.STORAGE] = system_info.disk_space / (1024 * 1024)  # Convert to MB
        
        logger.info(f"Discovered resources: {self.resources_by_type}")
    
    async def _monitoring_task(self):
        """Background task that monitors resource usage."""
        while self.running:
            try:
                # Get current system resource usage
                usage = self.system_monitor.get_resource_usage()
                
                # Update component usage based on monitoring data
                for component_id in self.component_resources:
                    # In a real implementation, we would have per-component monitoring
                    # For this example, we'll use the system monitor data as a proxy
                    if ResourceType.CPU in self.component_resources[component_id]:
                        cpu_usage = usage.cpu_percent / 100.0  # Convert to 0-1 range
                        self.component_resources[component_id][ResourceType.CPU].add_sample(cpu_usage)
                    
                    if ResourceType.MEMORY in self.component_resources[component_id]:
                        memory_usage = usage.memory_percent / 100.0
                        self.component_resources[component_id][ResourceType.MEMORY].add_sample(memory_usage)
                    
                    if ResourceType.STORAGE in self.component_resources[component_id]:
                        storage_usage = usage.disk_percent / 100.0
                        self.component_resources[component_id][ResourceType.STORAGE].add_sample(storage_usage)
                
                # Check for over-utilized resources and take action
                await self._optimize_resource_usage()
                
                # Predict future needs and prepare resources
                await self._predict_resource_needs()
                
                # Wait for next monitoring cycle
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in monitoring task: {e}")
                await asyncio.sleep(10)  # Wait a bit longer after an error
    
    async def _optimize_resource_usage(self):
        """Optimize resource allocation based on current usage."""
        for component_id, resources in self.component_resources.items():
            for resource_type, history in resources.items():
                # Get current usage metrics
                avg_usage = history.get_average_usage(30)  # 30 seconds average
                peak_usage = history.get_peak_usage(120)  # 2 minutes peak
                trend = history.get_trend()  # Usage trend
                
                # Current allocation
                current_allocation = history.allocation
                
                # Determine if adjustment is needed
                if avg_usage > current_allocation * 0.9:  # Using >90% of allocation
                    # Allocation is too tight, increase if possible
                    new_allocation = min(current_allocation * 1.2, peak_usage * 1.5)
                    await self._adjust_allocation(component_id, resource_type, new_allocation)
                    
                elif avg_usage < current_allocation * 0.6 and trend <= 0:  # Using <60% and not increasing
                    # Allocation is too generous, decrease to save resources
                    new_allocation = max(current_allocation * 0.8, avg_usage * 1.3)
                    await self._adjust_allocation(component_id, resource_type, new_allocation)
    
    async def _adjust_allocation(self, component_id: str, resource_type: ResourceType, new_allocation: float):
        """Adjust the resource allocation for a component."""
        # Check system capacity
        total_allocated = sum(res.get(resource_type, ResourceUsageHistory(component_id, resource_type)).allocation 
                            for comp_id, res in self.component_resources.items() 
                            if comp_id != component_id and resource_type in res)
        
        max_available = self.resources_by_type.get(resource_type, 0) * 0.95  # Keep 5% in reserve
        available_for_component = max_available - total_allocated
        
        if new_allocation > available_for_component:
            # Not enough resources available, cap at available amount
            new_allocation = available_for_component
            logger.warning(f"Resource {resource_type} allocation for {component_id} limited by system capacity")
        
        # Update the allocation
        old_allocation = self.component_resources[component_id][resource_type].allocation
        self.component_resources[component_id][resource_type].allocation = new_allocation
        
        logger.info(f"Adjusted {resource_type} allocation for {component_id}: {old_allocation:.2f} -> {new_allocation:.2f}")
        
        # Notify the component of the new allocation
        await self.message_bus.publish(
            "system.resource.allocation",
            {
                "component_id": component_id,
                "resource_type": resource_type.name,
                "allocation": new_allocation,
                "previous_allocation": old_allocation
            }
        )
    
    async def _predict_resource_needs(self):
        """Predict future resource needs based on trends and patterns."""
        # This would use more sophisticated algorithms in a real implementation
        # Here we just look at trends and make simple predictions
        for component_id, resources in self.component_resources.items():
            for resource_type, history in resources.items():
                trend = history.get_trend()
                
                if trend > 0.01:  # Significant upward trend
                    # Predict usage in next 5 minutes
                    avg_usage = history.get_average_usage(300)  # 5 minute average
                    predicted_usage = avg_usage + (trend * 300)  # Extrapolate 5 minutes ahead
                    
                    if predicted_usage > history.allocation * 0.9:
                        # Pre-emptively increase allocation if we predict high usage
                        new_allocation = min(history.allocation * 1.2, predicted_usage * 1.3)
                        await self._adjust_allocation(component_id, resource_type, new_allocation)
    
    async def _handle_resource_request(self, message: Dict[str, Any]):
        """Handle incoming resource request messages."""
        try:
            # Parse the request
            request = ResourceRequest(
                component_id=message["component_id"],
                resource_type=ResourceType[message["resource_type"]],
                requested_amount=message["requested_amount"],
                priority=Priority[message.get("priority", "NORMAL")]
            )
            
            # Process the request
            result = await self.handle_resource_request(request)
            
            # Send response
            await self.message_bus.publish(
                f"system.resource.response.{request.component_id}",
                {
                    "request_id": message.get("request_id"),
                    "component_id": request.component_id,
                    "resource_type": request.resource_type.name,
                    "requested_amount": request.requested_amount,
                    "allocated_amount": result.allocated_amount,
                    "success": result.success,
                    "message": result.message
                }
            )
        except Exception as e:
            logger.error(f"Error handling resource request: {e}")
            
            # Send error response
            await self.message_bus.publish(
                f"system.resource.response.{message.get('component_id', 'unknown')}",
                {
                    "request_id": message.get("request_id"),
                    "success": False,
                    "message": str(e)
                }
            )
    
    async def handle_resource_request(self, request: ResourceRequest) -> ResourceAllocation:
        """Process a resource allocation request."""
        component_id = request.component_id
        resource_type = request.resource_type
        requested_amount = request.requested_amount
        
        logger.info(f"Resource request from {component_id}: {resource_type}={requested_amount}")
        
        # Initialize component tracking if not exists
        if component_id not in self.component_resources:
            self.component_resources[component_id] = {}
        
        # Initialize resource tracking if not exists for this component
        if resource_type not in self.component_resources[component_id]:
            self.component_resources[component_id][resource_type] = ResourceUsageHistory(
                component_id=component_id,
                resource_type=resource_type
            )
        
        # Calculate total resources currently allocated for this type
        total_allocated = sum(res.get(resource_type, ResourceUsageHistory(comp_id, resource_type)).allocation 
                            for comp_id, res in self.component_resources.items() 
                            if comp_id != component_id and resource_type in res)
        
        # Current allocation for this component
        current_allocation = self.component_resources[component_id][resource_type].allocation
        
        # Calculate maximum available resources (keeping some reserve)
        total_available = self.resources_by_type.get(resource_type, 0)
        max_allocatable = total_available * 0.95  # Keep 5% in reserve
        available_for_component = max_allocatable - total_allocated
        
        # Determine how much to allocate
        if requested_amount <= available_for_component:
            # Can fulfill the request
            allocated_amount = requested_amount
            success = True
            message = "Resource request granted"
        else:
            # Cannot fully fulfill the request
            allocated_amount = available_for_component
            success = False
            message = f"Resource request partially granted. Requested: {requested_amount}, Allocated: {allocated_amount}"
            logger.warning(f"Insufficient {resource_type} for {component_id}: requested={requested_amount}, available={available_for_component}")
        
        # Update the allocation
        self.component_resources[component_id][resource_type].allocation = allocated_amount
        
        # Log the change if allocation changed
        if current_allocation != allocated_amount:
            logger.info(f"Allocated {resource_type} for {component_id}: {current_allocation} -> {allocated_amount}")
        
        return ResourceAllocation(
            component_id=component_id,
            resource_type=resource_type,
            requested_amount=requested_amount,
            allocated_amount=allocated_amount,
            success=success,
            message=message
        )
    
    async def _handle_resource_release(self, message: Dict[str, Any]):
        """Handle resource release messages."""
        try:
            component_id = message["component_id"]
            resource_type = ResourceType[message["resource_type"]]
            
            logger.info(f"Resource release from {component_id}: {resource_type}")
            
            # Check if component has this resource
            if component_id in self.component_resources and resource_type in self.component_resources[component_id]:
                # Get current allocation before releasing
                current_allocation = self.component_resources[component_id][resource_type].allocation
                
                # Release the resource
                self.component_resources[component_id][resource_type].allocation = 0
                
                logger.info(f"Released {resource_type} for {component_id}: {current_allocation} -> 0")
                
                # Send confirmation
                await self.message_bus.publish(
                    f"system.resource.release.response.{component_id}",
                    {
                        "request_id": message.get("request_id"),
                        "component_id": component_id,
                        "resource_type": resource_type.name,
                        "success": True,
                        "message": f"Resource {resource_type} released"
                    }
                )
            else:
                # Component didn't have this resource allocated
                logger.warning(f"Release request for unallocated resource: {component_id}, {resource_type}")
                
                await self.message_bus.publish(
                    f"system.resource.release.response.{component_id}",
                    {
                        "request_id": message.get("request_id"),
                        "component_id": component_id,
                        "resource_type": resource_type.name,
                        "success": False,
                        "message": f"Resource {resource_type} was not allocated to {component_id}"
                    }
                )
        except Exception as e:
            logger.error(f"Error handling resource release: {e}")
            
            # Send error response
            await self.message_bus.publish(
                f"system.resource.release.response.{message.get('component_id', 'unknown')}",
                {
                    "request_id": message.get("request_id"),
                    "success": False,
                    "message": str(e)
                }
            )
    
    async def _handle_component_started(self, message: Dict[str, Any]):
        """Handle component started messages."""
        component_id = message["component_id"]
        logger.info(f"Component started: {component_id}")
        
        # Initialize resource tracking for this component
        if component_id not in self.component_resources:
            self.component_resources[component_id] = {}
    
    async def _handle_component_stopped(self, message: Dict[str, Any]):
        """Handle component stopped messages."""
        component_id = message["component_id"]
        logger.info(f"Component stopped: {component_id}")
        
        # Release all resources for this component
        if component_id in self.component_resources:
            # Log resource release
            for resource_type, history in self.component_resources[component_id].items():
                if history.allocation > 0:
                    logger.info(f"Auto-releasing {resource_type} for stopped component {component_id}: {history.allocation} -> 0")
            
            # Remove the component from tracking
            del self.component_resources[component_id]