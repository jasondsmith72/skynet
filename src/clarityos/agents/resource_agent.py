"""
Resource Manager Agent

This agent is responsible for intelligent resource allocation and optimization
across the system. It monitors resource usage, predicts future demands, and
optimizes allocation to maximize performance and efficiency.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union
import random

from ..core.message_bus import MessagePriority, system_bus


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources that can be managed."""
    CPU = auto()
    MEMORY = auto()
    STORAGE = auto()
    NETWORK = auto()
    GPU = auto()
    IO = auto()


class ResourcePriority(Enum):
    """Priority levels for resource allocation."""
    CRITICAL = 0  # System critical processes
    HIGH = 1      # User-facing applications
    NORMAL = 2    # Standard background processes
    LOW = 3       # Batch processing, non-urgent tasks
    BACKGROUND = 4  # Idle tasks, maintenance


@dataclass
class ResourceRequest:
    """Request for resource allocation."""
    id: str
    process_id: str
    process_name: str
    resource_type: ResourceType
    amount: float  # Percentage or absolute amount based on resource type
    priority: ResourcePriority
    timestamp: float = field(default_factory=time.time)
    expiration: Optional[float] = None  # Optional expiration time for the request
    allocated: float = 0.0  # Amount actually allocated


@dataclass
class ResourceAllocation:
    """Current allocation of a resource."""
    resource_type: ResourceType
    total_capacity: float
    allocated: float = 0.0
    reserved: float = 0.0  # Reserved for critical processes
    last_updated: float = field(default_factory=time.time)
    allocations: Dict[str, ResourceRequest] = field(default_factory=dict)


@dataclass
class ResourceUsage:
    """Usage statistics for a resource."""
    resource_type: ResourceType
    current_usage: float
    peak_usage: float
    average_usage: float
    timestamp: float = field(default_factory=time.time)


class ResourceManagerAgent:
    """
    Agent responsible for intelligent resource allocation and optimization.
    
    This agent monitors system resource usage, predicts future demands based on
    usage patterns, and optimizes resource allocation to maximize performance and
    efficiency.
    """
    
    def __init__(self, agent_id: str, config: Dict):
        self.agent_id = agent_id
        self.config = config
        
        # Resource tracking
        self.resources: Dict[ResourceType, ResourceAllocation] = {}
        self.usage_history: Dict[ResourceType, List[ResourceUsage]] = {}
        self.pending_requests: List[ResourceRequest] = []
        
        # Settings
        self.history_size = config.get("history_size", 100)
        self.update_interval = config.get("update_interval", 5.0)  # seconds
        self.prediction_horizon = config.get("prediction_horizon", 60.0)  # seconds
        self.reservation_percentages = config.get("reservation_percentages", {
            ResourceType.CPU.name: 10.0,      # Reserve 10% CPU for critical processes
            ResourceType.MEMORY.name: 20.0,    # Reserve 20% memory
            ResourceType.STORAGE.name: 5.0,    # Reserve 5% storage
            ResourceType.NETWORK.name: 15.0,   # Reserve 15% network bandwidth
            ResourceType.GPU.name: 5.0,        # Reserve 5% GPU
            ResourceType.IO.name: 10.0         # Reserve 10% I/O
        })
        
        # Internal state
        self._shutdown_event = asyncio.Event()
        self._subscription_ids = []
        
    async def start(self):
        """Initialize the agent and subscribe to relevant messages."""
        logger.info(f"Starting ResourceManagerAgent (ID: {self.agent_id})")
        
        # Register message handlers
        self._subscription_ids.append(
            system_bus.subscribe(
                "resource.request",
                self._handle_resource_request,
                f"resource_agent_{self.agent_id}"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "resource.release",
                self._handle_resource_release,
                f"resource_agent_{self.agent_id}"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "system.process.started",
                self._handle_process_started,
                f"resource_agent_{self.agent_id}"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "system.process.terminated",
                self._handle_process_terminated,
                f"resource_agent_{self.agent_id}"
            )
        )
        
        # Initialize resource trackers
        await self._initialize_resources()
        
        # Report initialization complete
        await system_bus.publish(
            message_type="agent.status.update",
            content={
                "agent_id": self.agent_id,
                "status": "running",
                "message": "Resource manager initialized"
            },
            source=f"resource_agent_{self.agent_id}"
        )
    
    async def stop(self):
        """Clean up and stop the agent."""
        logger.info(f"Stopping ResourceManagerAgent (ID: {self.agent_id})")
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Unsubscribe from messages
        for subscription_id in self._subscription_ids:
            system_bus.unsubscribe("*", subscription_id)
        
        # Release all resources
        for resource_type, allocation in self.resources.items():
            for request_id in list(allocation.allocations.keys()):
                await self._release_resource(request_id)
        
        # Report shutdown
        await system_bus.publish(
            message_type="agent.status.update",
            content={
                "agent_id": self.agent_id,
                "status": "stopped",
                "message": "Resource manager stopped"
            },
            source=f"resource_agent_{self.agent_id}"
        )
    
    async def run(self):
        """Main agent loop for continuous monitoring and optimization."""
        while not self._shutdown_event.is_set():
            try:
                # Update resource usage stats
                await self._update_resource_usage()
                
                # Process pending requests
                await self._process_pending_requests()
                
                # Run optimization algorithm
                await self._optimize_allocations()
                
                # Report current state
                await self._report_status()
                
                # Wait for next update cycle
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), self.update_interval)
                except asyncio.TimeoutError:
                    pass
                
            except Exception as e:
                logger.error(f"Error in ResourceManagerAgent main loop: {str(e)}", exc_info=True)
                
                # Brief pause to avoid tight error loops
                await asyncio.sleep(1.0)
    
    async def _initialize_resources(self):
        """Initialize resource tracking from system information."""
        # For each resource type, get capacity and initialize tracking
        for resource_type in ResourceType:
            capacity = await self._get_resource_capacity(resource_type)
            
            reservation = self.reservation_percentages.get(resource_type.name, 0.0)
            reserved_amount = capacity * (reservation / 100.0)
            
            self.resources[resource_type] = ResourceAllocation(
                resource_type=resource_type,
                total_capacity=capacity,
                reserved=reserved_amount
            )
            
            self.usage_history[resource_type] = []
            
            logger.info(f"Initialized {resource_type.name} tracking: "
                       f"capacity={capacity}, reserved={reserved_amount}")
    
    async def _get_resource_capacity(self, resource_type: ResourceType) -> float:
        """Get the total capacity of a resource from the system."""
        # In a real implementation, this would query the system
        # For now, return placeholder values
        
        # Simulated capacity values
        capacities = {
            ResourceType.CPU: 100.0,  # 100% of all CPUs
            ResourceType.MEMORY: 16384.0,  # 16 GB in MB
            ResourceType.STORAGE: 512000.0,  # 500 GB in MB
            ResourceType.NETWORK: 1000.0,  # 1000 Mbps
            ResourceType.GPU: 100.0,  # 100% of GPU
            ResourceType.IO: 100.0,  # 100% of I/O capacity
        }
        
        # Return the simulated capacity or a default
        return capacities.get(resource_type, 100.0)
    
    async def _update_resource_usage(self):
        """Update current resource usage statistics."""
        for resource_type in ResourceType:
            # In a real implementation, would query actual system stats
            # For now, use simulated values
            current_usage = await self._get_current_usage(resource_type)
            
            # Get historical data for this resource
            history = self.usage_history[resource_type]
            
            # Calculate peak and average if we have history
            if history:
                peak_usage = max(current_usage, max(entry.current_usage for entry in history))
                average_usage = sum(entry.current_usage for entry in history) / len(history)
            else:
                peak_usage = current_usage
                average_usage = current_usage
            
            # Create usage record
            usage = ResourceUsage(
                resource_type=resource_type,
                current_usage=current_usage,
                peak_usage=peak_usage,
                average_usage=average_usage
            )
            
            # Add to history
            history.append(usage)
            
            # Trim history if needed
            if len(history) > self.history_size:
                self.usage_history[resource_type] = history[-self.history_size:]
    
    async def _get_current_usage(self, resource_type: ResourceType) -> float:
        """Get the current usage of a resource from the system."""
        # In a real implementation, this would query actual system stats
        # For now, return simulated values based on allocations
        
        # Get the allocation for this resource
        allocation = self.resources.get(resource_type)
        if not allocation:
            return 0.0
        
        # Simulate actual usage as 80-120% of allocated amount
        # (some processes use less than allocated, some use more)
        usage_factor = random.uniform(0.8, 1.2)
        
        # Calculate usage
        usage = allocation.allocated * usage_factor
        
        # Add some minimum system overhead
        min_usage = allocation.total_capacity * 0.05  # 5% minimum usage
        usage = max(usage, min_usage)
        
        # Ensure usage doesn't exceed capacity
        usage = min(usage, allocation.total_capacity)
        
        return usage
    
    async def _process_pending_requests(self):
        """Process any pending resource requests."""
        if not self.pending_requests:
            return
        
        # Process requests in priority order
        self.pending_requests.sort(key=lambda r: r.priority.value)
        
        # Try to allocate resources for each pending request
        remaining_requests = []
        for request in self.pending_requests:
            success, amount = await self._allocate_resource(request)
            
            if not success:
                remaining_requests.append(request)
        
        # Update pending requests list
        self.pending_requests = remaining_requests
    
    async def _allocate_resource(self, request: ResourceRequest) -> Tuple[bool, float]:
        """
        Attempt to allocate a resource based on a request.
        
        Returns:
            Tuple of (success, amount_allocated)
        """
        resource_type = request.resource_type
        
        # Get the allocation for this resource
        if resource_type not in self.resources:
            logger.warning(f"Resource type {resource_type} not initialized")
            return False, 0.0
        
        allocation = self.resources[resource_type]
        
        # Check if we have enough available capacity
        available = allocation.total_capacity - allocation.allocated - allocation.reserved
        
        # For critical requests, we can use the reserved capacity
        if request.priority == ResourcePriority.CRITICAL:
            available += allocation.reserved
        
        # Check if we have enough
        if available < request.amount:
            # Not enough available
            if request.priority.value <= ResourcePriority.HIGH.value:
                # For high-priority requests, allocate what we can
                amount_to_allocate = available
            else:
                # For lower priority, don't allocate partial amount
                return False, 0.0
        else:
            # We have enough
            amount_to_allocate = request.amount
        
        # Update the request
        request.allocated = amount_to_allocate
        
        # Update the allocation
        allocation.allocations[request.id] = request
        allocation.allocated += amount_to_allocate
        allocation.last_updated = time.time()
        
        # Log the allocation
        logger.info(f"Allocated {amount_to_allocate} of {resource_type.name} "
                   f"to process {request.process_name} (ID: {request.process_id})")
        
        # Notify about the allocation
        await system_bus.publish(
            message_type="resource.allocated",
            content={
                "request_id": request.id,
                "process_id": request.process_id,
                "resource_type": resource_type.name,
                "amount": amount_to_allocate,
                "timestamp": time.time()
            },
            source=f"resource_agent_{self.agent_id}",
            priority=MessagePriority.HIGH
        )
        
        return True, amount_to_allocate
    
    async def _release_resource(self, request_id: str) -> bool:
        """
        Release a previously allocated resource.
        
        Args:
            request_id: ID of the allocation request to release
            
        Returns:
            True if resource was found and released, False otherwise
        """
        # Find the allocation containing this request
        for resource_type, allocation in self.resources.items():
            if request_id in allocation.allocations:
                request = allocation.allocations[request_id]
                
                # Update the allocation
                allocation.allocated -= request.allocated
                allocation.last_updated = time.time()
                
                # Remove the request
                del allocation.allocations[request_id]
                
                # Log the release
                logger.info(f"Released {request.allocated} of {resource_type.name} "
                           f"from process {request.process_name} (ID: {request.process_id})")
                
                # Notify about the release
                await system_bus.publish(
                    message_type="resource.released",
                    content={
                        "request_id": request_id,
                        "process_id": request.process_id,
                        "resource_type": resource_type.name,
                        "amount": request.allocated,
                        "timestamp": time.time()
                    },
                    source=f"resource_agent_{self.agent_id}",
                    priority=MessagePriority.NORMAL
                )
                
                return True
        
        # Request not found
        logger.warning(f"Resource request {request_id} not found for release")
        return False
    
    async def _optimize_allocations(self):
        """
        Run optimization algorithm to improve resource allocations.
        
        This method analyzes current usage patterns and adjusts allocations
        to better match actual needs.
        """
        for resource_type, allocation in self.resources.items():
            # Skip if no allocations
            if not allocation.allocations:
                continue
            
            # Get usage history for this resource
            history = self.usage_history.get(resource_type, [])
            if not history:
                continue
            
            # Calculate current usage efficiency
            current_usage = history[-1].current_usage
            usage_efficiency = current_usage / allocation.allocated if allocation.allocated > 0 else 1.0
            
            # If efficiency is very low, we're over-allocating
            if usage_efficiency < 0.7:  # Using less than 70% of allocation
                # Find processes using less than their allocation
                for request_id, request in list(allocation.allocations.items()):
                    # Skip critical processes
                    if request.priority == ResourcePriority.CRITICAL:
                        continue
                    
                    # Calculate a new allocation based on actual usage
                    # (In a real implementation, would check process-specific usage)
                    new_allocation = request.allocated * 0.8  # Reduce to 80% of current
                    
                    # Ensure minimum allocation
                    new_allocation = max(new_allocation, request.amount * 0.5)
                    
                    # Only adjust if the change is significant
                    if abs(new_allocation - request.allocated) / request.allocated > 0.1:  # >10% change
                        # Update the allocation
                        delta = new_allocation - request.allocated
                        request.allocated = new_allocation
                        allocation.allocated += delta
                        
                        logger.info(f"Optimized {resource_type.name} allocation for "
                                   f"{request.process_name}: {request.allocated - delta} -> {request.allocated}")
                        
                        # Notify about the adjustment
                        await system_bus.publish(
                            message_type="resource.adjusted",
                            content={
                                "request_id": request_id,
                                "process_id": request.process_id,
                                "resource_type": resource_type.name,
                                "old_amount": request.allocated - delta,
                                "new_amount": request.allocated,
                                "timestamp": time.time()
                            },
                            source=f"resource_agent_{self.agent_id}",
                            priority=MessagePriority.LOW
                        )
    
    async def _report_status(self):
        """Report current resource status to the system."""
        status = {
            "resources": {},
            "timestamp": time.time()
        }
        
        for resource_type, allocation in self.resources.items():
            # Get latest usage if available
            history = self.usage_history.get(resource_type, [])
            current_usage = history[-1].current_usage if history else 0.0
            
            status["resources"][resource_type.name] = {
                "total_capacity": allocation.total_capacity,
                "allocated": allocation.allocated,
                "reserved": allocation.reserved,
                "current_usage": current_usage,
                "allocation_count": len(allocation.allocations)
            }
        
        # Report metrics
        await system_bus.publish(
            message_type="agent.status.update",
            content={
                "agent_id": self.agent_id,
                "status": "running",
                "metrics": {
                    "resource_status": status
                }
            },
            source=f"resource_agent_{self.agent_id}",
            priority=MessagePriority.LOW
        )
    
    # Message handlers
    
    async def _handle_resource_request(self, message):
        """Handle resource allocation requests."""
        content = message.content
        
        try:
            # Create request object
            request = ResourceRequest(
                id=content.get("request_id", str(uuid.uuid4())),
                process_id=content["process_id"],
                process_name=content["process_name"],
                resource_type=ResourceType[content["resource_type"]],
                amount=float(content["amount"]),
                priority=ResourcePriority[content["priority"]] if "priority" in content else ResourcePriority.NORMAL,
                expiration=content.get("expiration")
            )
            
            # Add to pending requests
            self.pending_requests.append(request)
            
            # Try immediate allocation if high priority
            if request.priority.value <= ResourcePriority.HIGH.value:
                success, amount = await self._allocate_resource(request)
                
                if success:
                    # Remove from pending if allocated
                    self.pending_requests.remove(request)
                    
                    if message.reply_to:
                        await system_bus.publish(
                            message_type=f"{message.message_type}.reply",
                            content={
                                "success": True,
                                "request_id": request.id,
                                "amount": amount
                            },
                            source=f"resource_agent_{self.agent_id}",
                            reply_to=message.source
                        )
                else:
                    # Respond with pending status
                    if message.reply_to:
                        await system_bus.publish(
                            message_type=f"{message.message_type}.reply",
                            content={
                                "success": False,
                                "request_id": request.id,
                                "message": "Request queued, insufficient resources"
                            },
                            source=f"resource_agent_{self.agent_id}",
                            reply_to=message.source
                        )
            else:
                # Just acknowledge the request for lower priorities
                if message.reply_to:
                    await system_bus.publish(
                        message_type=f"{message.message_type}.reply",
                        content={
                            "success": True,
                            "request_id": request.id,
                            "message": "Request queued"
                        },
                        source=f"resource_agent_{self.agent_id}",
                        reply_to=message.source
                    )
        
        except Exception as e:
            logger.error(f"Error handling resource request: {str(e)}")
            
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "message": f"Error: {str(e)}"
                    },
                    source=f"resource_agent_{self.agent_id}",
                    reply_to=message.source
                )
    
    async def _handle_resource_release(self, message):
        """Handle resource release requests."""
        content = message.content
        
        try:
            request_id = content["request_id"]
            
            # Try to release the resource
            success = await self._release_resource(request_id)
            
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": success,
                        "request_id": request_id
                    },
                    source=f"resource_agent_{self.agent_id}",
                    reply_to=message.source
                )
        
        except Exception as e:
            logger.error(f"Error handling resource release: {str(e)}")
            
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "message": f"Error: {str(e)}"
                    },
                    source=f"resource_agent_{self.agent_id}",
                    reply_to=message.source
                )
    
    async def _handle_process_started(self, message):
        """Handle process start notifications."""
        # When a process starts, we don't automatically allocate resources
        # The process should request resources explicitly
        # This handler is for informational purposes and learning patterns
        content = message.content
        logger.debug(f"Process started: {content.get('process_name')} (ID: {content.get('process_id')})")
    
    async def _handle_process_terminated(self, message):
        """Handle process termination notifications."""
        # When a process terminates, release all its resources
        content = message.content
        process_id = content.get("process_id")
        
        if not process_id:
            return
        
        # Find and release all resources allocated to this process
        for resource_type, allocation in self.resources.items():
            for request_id, request in list(allocation.allocations.items()):
                if request.process_id == process_id:
                    await self._release_resource(request_id)
