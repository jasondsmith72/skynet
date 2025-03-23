"""
Memory Manager for ClarityOS

This module provides memory management for ClarityOS, handling memory allocation,
prioritization, and optimization for AI operations.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple

from clarityos.core.message_bus import MessagePriority, system_bus

# Configure logging
logger = logging.getLogger(__name__)


class MemoryPriority(Enum):
    """Priority levels for memory allocation."""
    CRITICAL = 0  # System essential functions
    HIGH = 1      # User-facing operations
    MEDIUM = 2    # Important background processes
    LOW = 3       # Non-essential processes
    BACKGROUND = 4  # Processes that can be swapped


class MemoryRegionType(Enum):
    """Types of memory regions."""
    SYSTEM = "system"        # Core OS components
    AI_MODEL = "ai_model"    # AI model weights and activations
    USER = "user"            # User applications
    BUFFER = "buffer"        # I/O and communication buffers
    CACHE = "cache"          # Cached data
    SHARED = "shared"        # Shared memory regions


@dataclass
class MemoryRegion:
    """Represents a region of memory allocated for a specific purpose."""
    id: str
    name: str
    type: MemoryRegionType
    size_mb: float
    priority: MemoryPriority
    owner: str  # Component or agent that owns this region
    is_pinned: bool = False  # Whether the region can be swapped out
    is_shared: bool = False  # Whether the region is shared between components
    creation_time: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryAllocationRequest:
    """Request for memory allocation."""
    size_mb: float
    type: MemoryRegionType
    priority: MemoryPriority
    owner: str
    is_pinned: bool = False
    is_shared: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryStats:
    """Statistics about memory usage."""
    total_mb: float = 0.0
    available_mb: float = 0.0
    used_mb: float = 0.0
    system_mb: float = 0.0
    ai_model_mb: float = 0.0
    user_mb: float = 0.0
    buffer_mb: float = 0.0
    cache_mb: float = 0.0
    shared_mb: float = 0.0
    swap_total_mb: float = 0.0
    swap_used_mb: float = 0.0
    last_updated: float = field(default_factory=time.time)


class MemoryManager:
    """
    Intelligent memory management system for ClarityOS.
    """
    
    def __init__(self):
        """Initialize the memory manager."""
        self.regions: Dict[str, MemoryRegion] = {}
        self.stats = MemoryStats()
        self.config: Dict[str, Any] = {
            'total_memory_mb': 0.0,
            'min_available_mb': 512.0,
            'swap_threshold_mb': 1024.0,
            'enable_predictive_allocation': True,
            'allocation_learning_rate': 0.2,
            'priority_boost_duration': 30.0,
        }
        self._initialized = False
        self._monitoring_task = None
        self._optimization_task = None
        self._next_region_id = 1
    
    async def initialize(self) -> bool:
        """Initialize the memory manager."""
        if self._initialized:
            logger.warning("Memory manager already initialized")
            return True
        
        logger.info("Initializing memory manager")
        
        try:
            # Detect available memory
            await self._detect_memory()
            
            # Subscribe to memory-related messages
            await self._subscribe_to_messages()
            
            # Start monitoring and optimization tasks
            self._monitoring_task = asyncio.create_task(self._monitor_memory())
            self._optimization_task = asyncio.create_task(self._optimize_memory())
            
            # Initialize system memory regions
            await self._init_system_regions()
            
            self._initialized = True
            logger.info(f"Memory manager initialized with {self.stats.total_mb:.2f}MB total memory")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing memory manager: {str(e)}", exc_info=True)
            return False
    
    async def _detect_memory(self):
        """Detect available memory in the system."""
        # In a real OS, this would directly access memory information
        # For now, we'll simulate it with reasonable defaults
        
        # Detect physical memory (simulated)
        self.stats.total_mb = 16384.0  # 16GB
        self.stats.available_mb = 14336.0  # 14GB initially available
        self.stats.used_mb = 2048.0  # 2GB used by system processes
        
        # Detect swap space (simulated)
        self.stats.swap_total_mb = 8192.0  # 8GB
        self.stats.swap_used_mb = 0.0  # None used initially
        
        # Update configuration
        self.config['total_memory_mb'] = self.stats.total_mb
        
        logger.info(f"Detected {self.stats.total_mb:.2f}MB total memory, "
                   f"{self.stats.available_mb:.2f}MB available")
    
    async def _subscribe_to_messages(self):
        """Subscribe to memory-related messages on the system bus."""
        system_bus.subscribe("memory.allocate", self._handle_allocate_request, "memory_manager")
        system_bus.subscribe("memory.free", self._handle_free_request, "memory_manager")
        system_bus.subscribe("memory.query", self._handle_query_request, "memory_manager")
        system_bus.subscribe("memory.priority.update", self._handle_priority_update, "memory_manager")
    
    async def _init_system_regions(self):
        """Initialize memory regions for critical system components."""
        # Allocate memory for essential system components
        system_core_request = MemoryAllocationRequest(
            size_mb=512.0,
            type=MemoryRegionType.SYSTEM,
            priority=MemoryPriority.CRITICAL,
            owner="system_core",
            is_pinned=True,
            metadata={"description": "Core system components"}
        )
        await self.allocate_memory(system_core_request)
        
        # Allocate memory for AI foundation models
        ai_core_request = MemoryAllocationRequest(
            size_mb=4096.0,
            type=MemoryRegionType.AI_MODEL,
            priority=MemoryPriority.HIGH,
            owner="ai_core",
            is_pinned=True,
            metadata={"description": "Foundation AI models"}
        )
        await self.allocate_memory(ai_core_request)
        
        # Allocate memory for buffer pools
        buffer_request = MemoryAllocationRequest(
            size_mb=256.0,
            type=MemoryRegionType.BUFFER,
            priority=MemoryPriority.MEDIUM,
            owner="system_io",
            is_shared=True,
            metadata={"description": "I/O buffer pools"}
        )
        await self.allocate_memory(buffer_request)
    
    async def _monitor_memory(self):
        """Periodically monitor memory usage and status."""
        try:
            while True:
                # Update memory usage by type
                self._update_memory_stats()
                
                # Publish memory stats
                await self._publish_memory_stats()
                
                # Check for memory pressure
                if self.stats.available_mb < self.config['min_available_mb']:
                    await self._handle_memory_pressure()
                
                # Check again after 10 seconds
                await asyncio.sleep(10)
                
        except asyncio.CancelledError:
            logger.info("Memory monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in memory monitoring task: {str(e)}", exc_info=True)
    
    def _update_memory_stats(self):
        """Update memory usage statistics."""
        # Calculate memory usage by type
        system_mb = sum(r.size_mb for r in self.regions.values() if r.type == MemoryRegionType.SYSTEM)
        ai_model_mb = sum(r.size_mb for r in self.regions.values() if r.type == MemoryRegionType.AI_MODEL)
        user_mb = sum(r.size_mb for r in self.regions.values() if r.type == MemoryRegionType.USER)
        buffer_mb = sum(r.size_mb for r in self.regions.values() if r.type == MemoryRegionType.BUFFER)
        cache_mb = sum(r.size_mb for r in self.regions.values() if r.type == MemoryRegionType.CACHE)
        shared_mb = sum(r.size_mb for r in self.regions.values() if r.is_shared)
        
        # Update stats
        self.stats.system_mb = system_mb
        self.stats.ai_model_mb = ai_model_mb
        self.stats.user_mb = user_mb
        self.stats.buffer_mb = buffer_mb
        self.stats.cache_mb = cache_mb
        self.stats.shared_mb = shared_mb
        
        total_allocated = system_mb + ai_model_mb + user_mb + buffer_mb + cache_mb
        
        # Account for shared memory only once
        total_allocated -= shared_mb
        
        # Update used and available memory
        self.stats.used_mb = total_allocated
        self.stats.available_mb = self.stats.total_mb - total_allocated
        self.stats.last_updated = time.time()
    
    async def _publish_memory_stats(self):
        """Publish memory statistics to the system bus."""
        await system_bus.publish(
            message_type="memory.stats.updated",
            content={"stats": {k: getattr(self.stats, k) for k in self.stats.__annotations__}},
            source="memory_manager",
            priority=MessagePriority.LOW
        )
    
    async def _optimize_memory(self):
        """Periodically optimize memory usage based on access patterns."""
        try:
            while True:
                # Run optimization every 60 seconds
                await asyncio.sleep(60)
                
                # Skip if not enough regions to optimize
                if len(self.regions) < 5:
                    continue
                
                logger.info("Running memory optimization")
                
                # Find candidates for optimization
                candidates = self._find_optimization_candidates()
                
                # If under memory pressure, release some regions
                if self.stats.available_mb < self.config['swap_threshold_mb']:
                    await self._release_memory_pressure(candidates)
                
        except asyncio.CancelledError:
            logger.info("Memory optimization task cancelled")
        except Exception as e:
            logger.error(f"Error in memory optimization task: {str(e)}", exc_info=True)
    
    def _find_optimization_candidates(self):
        """Find memory regions that could be released or swapped."""
        now = time.time()
        candidates = []
        
        for region_id, region in self.regions.items():
            # Skip pinned regions
            if region.is_pinned:
                continue
            
            # Calculate a score based on priority, access pattern, and size
            priority_score = region.priority.value * 100  # Higher value = lower priority
            time_score = (now - region.last_accessed) / 60.0  # Minutes since last access
            size_score = region.size_mb / 100.0  # Larger regions get higher scores
            
            # Adjust for access frequency
            frequency_factor = 10.0 / max(1, region.access_count)
            
            total_score = (priority_score + time_score + size_score) * frequency_factor
            
            candidates.append((region_id, total_score))
        
        # Sort by score (highest first = best to release)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates
    
    async def _release_memory_pressure(self, candidates):
        """Release memory to alleviate pressure."""
        logger.info(f"Memory pressure detected: {self.stats.available_mb:.2f}MB available")
        
        # Calculate how much we need to free
        target_to_free = self.config['swap_threshold_mb'] - self.stats.available_mb
        
        # Try to free up memory
        freed_mb = 0.0
        for region_id, score in candidates:
            if freed_mb >= target_to_free:
                break
            
            region = self.regions[region_id]
            
            # For cache regions, we can just free them
            if region.type == MemoryRegionType.CACHE:
                logger.info(f"Freeing cache region {region.name} ({region.size_mb:.2f}MB)")
                await self.free_memory(region_id)
                freed_mb += region.size_mb
            
            # For other regions, we'd swap them out in a real OS
            elif region.type in (MemoryRegionType.USER, MemoryRegionType.AI_MODEL):
                logger.info(f"Would swap out region {region.name} ({region.size_mb:.2f}MB)")
                # In a real implementation, this would move the region to swap
        
        logger.info(f"Memory optimization freed {freed_mb:.2f}MB")
    
    async def _handle_memory_pressure(self):
        """Handle low memory conditions."""
        logger.warning(f"Memory pressure detected: {self.stats.available_mb:.2f}MB available")
        
        # Emit memory pressure warning
        await system_bus.publish(
            message_type="memory.pressure",
            content={
                "available_mb": self.stats.available_mb,
                "threshold_mb": self.config['min_available_mb'],
                "severity": "high" if self.stats.available_mb < (self.config['min_available_mb'] / 2) else "medium"
            },
            source="memory_manager",
            priority=MessagePriority.HIGH
        )
        
        # Find cache regions that can be released
        cache_regions = [r for r in self.regions.values() 
                        if r.type == MemoryRegionType.CACHE and not r.is_pinned]
        
        # Sort by priority and last access time
        cache_regions.sort(key=lambda r: (r.priority.value, -r.last_accessed))
        
        # Try to free enough memory
        target_to_free = self.config['min_available_mb'] - self.stats.available_mb
        freed_mb = 0.0
        
        for region in cache_regions:
            if freed_mb >= target_to_free:
                break
            
            logger.info(f"Freeing cache region {region.name} ({region.size_mb:.2f}MB) due to memory pressure")
            await self.free_memory(region.id)
            freed_mb += region.size_mb
    
    async def allocate_memory(self, request: MemoryAllocationRequest) -> Tuple[bool, str, Optional[str]]:
        """
        Allocate memory based on a request.
        
        Args:
            request: Memory allocation request
            
        Returns:
            Tuple of (success, message, region_id)
        """
        # Check if we have enough memory
        if request.size_mb > self.stats.available_mb:
            logger.warning(f"Not enough memory to allocate {request.size_mb:.2f}MB")
            return False, f"Not enough memory available ({self.stats.available_mb:.2f}MB)", None
        
        # Generate a unique ID for the region
        region_id = f"region-{self._next_region_id}"
        self._next_region_id += 1
        
        # Create the memory region
        region = MemoryRegion(
            id=region_id,
            name=f"{request.owner}-{request.type.value}",
            type=request.type,
            size_mb=request.size_mb,
            priority=request.priority,
            owner=request.owner,
            is_pinned=request.is_pinned,
            is_shared=request.is_shared,
            metadata=request.metadata
        )
        
        # Store the region
        self.regions[region_id] = region
        
        logger.info(f"Allocated {request.size_mb:.2f}MB for {request.owner} ({request.type.value})")
        
        # Update memory stats
        self._update_memory_stats()
        
        return True, f"Allocated {request.size_mb:.2f}MB of {request.type.value} memory", region_id
    
    async def free_memory(self, region_id: str) -> Tuple[bool, str]:
        """
        Free a memory region.
        
        Args:
            region_id: ID of the region to free
            
        Returns:
            Tuple of (success, message)
        """
        if region_id not in self.regions:
            return False, f"Region {region_id} not found"
        
        region = self.regions[region_id]
        
        # Remove the region
        del self.regions[region_id]
        
        logger.info(f"Freed {region.size_mb:.2f}MB of {region.type.value} memory from {region.owner}")
        
        # Update memory stats
        self._update_memory_stats()
        
        return True, f"Freed {region.size_mb:.2f}MB of {region.type.value} memory"
    
    async def update_region_priority(self, region_id: str, priority: MemoryPriority) -> Tuple[bool, str]:
        """
        Update the priority of a memory region.
        
        Args:
            region_id: ID of the region
            priority: New priority
            
        Returns:
            Tuple of (success, message)
        """
        if region_id not in self.regions:
            return False, f"Region {region_id} not found"
        
        region = self.regions[region_id]
        old_priority = region.priority
        region.priority = priority
        
        logger.info(f"Updated region {region.name} priority from {old_priority} to {priority}")
        
        return True, f"Updated priority from {old_priority} to {priority}"
    
    async def access_memory(self, region_id: str) -> Tuple[bool, str]:
        """
        Record memory access to a region.
        
        Args:
            region_id: ID of the region
            
        Returns:
            Tuple of (success, message)
        """
        if region_id not in self.regions:
            return False, f"Region {region_id} not found"
        
        region = self.regions[region_id]
        region.last_accessed = time.time()
        region.access_count += 1
        
        return True, f"Recorded access to region {region.name}"
    
    async def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        return self.stats
    
    async def get_region_info(self, region_id: str) -> Optional[MemoryRegion]:
        """Get information about a specific memory region."""
        return self.regions.get(region_id)
    
    async def get_all_regions(self) -> Dict[str, MemoryRegion]:
        """Get information about all memory regions."""
        return self.regions
    
    async def _handle_allocate_request(self, message):
        """Handle memory allocation requests from the system bus."""
        content = message.content
        
        request = MemoryAllocationRequest(
            size_mb=content["size_mb"],
            type=MemoryRegionType(content["type"]),
            priority=MemoryPriority(content["priority"]),
            owner=content["owner"],
            is_pinned=content.get("is_pinned", False),
            is_shared=content.get("is_shared", False),
            metadata=content.get("metadata", {})
        )
        
        success, message_text, region_id = await self.allocate_memory(request)
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "message": message_text,
                    "region_id": region_id
                },
                source="memory_manager",
                reply_to=message.source
            )
    
    async def _handle_free_request(self, message):
        """Handle memory free requests from the system bus."""
        content = message.content
        region_id = content["region_id"]
        
        success, message_text = await self.free_memory(region_id)
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "message": message_text
                },
                source="memory_manager",
                reply_to=message.source
            )
    
    async def _handle_query_request(self, message):
        """Handle memory query requests from the system bus."""
        content = message.content
        query_type = content.get("type", "stats")
        
        result = {}
        
        if query_type == "stats":
            # Get overall memory stats
            stats = await self.get_memory_stats()
            result["stats"] = {k: getattr(stats, k) for k in stats.__annotations__}
            
        elif query_type == "region":
            # Get info about a specific region
            region_id = content.get("region_id")
            if region_id:
                region = await self.get_region_info(region_id)
                if region:
                    result["region"] = {
                        "id": region.id,
                        "name": region.name,
                        "type": region.type.value,
                        "size_mb": region.size_mb,
                        "priority": region.priority.value,
                        "owner": region.owner,
                        "is_pinned": region.is_pinned,
                        "is_shared": region.is_shared
                    }
                else:
                    result["error"] = f"Region {region_id} not found"
            else:
                result["error"] = "No region_id specified"
                
        elif query_type == "regions":
            # Get info about all regions
            regions = await self.get_all_regions()
            result["regions"] = [
                {
                    "id": r.id,
                    "name": r.name,
                    "type": r.type.value,
                    "size_mb": r.size_mb,
                    "priority": r.priority.value,
                    "owner": r.owner
                }
                for r in regions.values()
            ]
        
        else:
            result["error"] = f"Unknown query type: {query_type}"
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content=result,
                source="memory_manager",
                reply_to=message.source
            )
    
    async def _handle_priority_update(self, message):
        """Handle memory priority update requests from the system bus."""
        content = message.content
        region_id = content["region_id"]
        priority = MemoryPriority(content["priority"])
        
        success, message_text = await self.update_region_priority(region_id, priority)
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "message": message_text
                },
                source="memory_manager",
                reply_to=message.source
            )
    
    async def shutdown(self):
        """Shut down the memory manager."""
        logger.info("Shutting down memory manager")
        
        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Cancel optimization task
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
        
        self._initialized = False
        logger.info("Memory manager shutdown complete")


# Singleton instance
memory_manager = MemoryManager()
