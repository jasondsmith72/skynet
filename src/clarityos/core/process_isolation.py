"""
Process Isolation System for ClarityOS

This module provides secure process isolation capabilities, creating
boundaries between different system components and enforcing capability-based
security policies.
"""

import asyncio
import logging
import os
import platform
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set, Tuple, Callable

from clarityos.core.message_bus import MessagePriority, system_bus

# Configure logging
logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for isolated processes."""
    SYSTEM = 0      # Highest privileges - core system components
    PRIVILEGED = 1  # Elevated privileges - critical system agents
    STANDARD = 2    # Normal privileges - trusted user agents
    RESTRICTED = 3  # Limited privileges - untrusted user agents
    SANDBOX = 4     # Minimal privileges - potentially unsafe code


class ProcessCapability(Enum):
    """Capabilities that can be granted to processes."""
    # Hardware access capabilities
    HARDWARE_ACCESS = auto()
    MEMORY_MANAGEMENT = auto()
    NETWORK_ACCESS = auto()
    STORAGE_ACCESS = auto()
    
    # System capabilities
    PROCESS_MANAGEMENT = auto()
    SERVICE_MANAGEMENT = auto()
    AGENT_MANAGEMENT = auto()
    
    # Communication capabilities
    MESSAGE_BUS_ACCESS = auto()
    SYSTEM_MESSAGING = auto()
    AGENT_MESSAGING = auto()
    
    # User data capabilities
    USER_DATA_READ = auto()
    USER_DATA_WRITE = auto()
    
    # Learning capabilities
    MODEL_ACCESS = auto()
    LEARNING_WRITE = auto()
    
    # Security-related capabilities
    SECURITY_POLICY = auto()
    CAPABILITY_GRANT = auto()


@dataclass
class ProcessIsolationPolicy:
    """Defines security policies for an isolated process."""
    security_level: SecurityLevel
    capabilities: Set[ProcessCapability] = field(default_factory=set)
    allowed_resources: Dict[str, List[str]] = field(default_factory=dict)
    memory_limit_mb: Optional[float] = None
    cpu_limit_percent: Optional[float] = None
    network_limit_mbps: Optional[float] = None
    allowed_message_types: Optional[List[str]] = None
    timeout_seconds: Optional[float] = None
    require_verification: bool = False


@dataclass
class IsolatedProcess:
    """Represents an isolated process."""
    id: str
    name: str
    owner: str
    policy: ProcessIsolationPolicy
    process_handle: Any = None
    status: str = "initialized"
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    resource_usage: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProcessIsolationManager:
    """
    Manages process isolation for ClarityOS.
    
    This class creates secure execution environments for different components,
    enforcing capability-based security policies and resource limits.
    """
    
    def __init__(self):
        """Initialize the process isolation manager."""
        self.processes: Dict[str, IsolatedProcess] = {}
        self.default_policies: Dict[SecurityLevel, ProcessIsolationPolicy] = {}
        self.capability_verifiers: Dict[ProcessCapability, Callable] = {}
        self._initialized = False
        self._monitoring_task = None
    
    async def initialize(self) -> bool:
        """
        Initialize the process isolation manager.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        if self._initialized:
            logger.warning("Process isolation manager already initialized")
            return True
        
        logger.info("Initializing process isolation manager")
        
        try:
            # Create default policies
            self._create_default_policies()
            
            # Set up capability verifiers
            self._setup_capability_verifiers()
            
            # Subscribe to process-related messages
            await self._subscribe_to_messages()
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitor_processes())
            
            self._initialized = True
            logger.info("Process isolation manager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing process isolation manager: {str(e)}", exc_info=True)
            return False
    
    def _create_default_policies(self):
        """Create default security policies for different security levels."""
        # System level policy (highest privileges)
        system_policy = ProcessIsolationPolicy(
            security_level=SecurityLevel.SYSTEM,
            capabilities={
                ProcessCapability.HARDWARE_ACCESS,
                ProcessCapability.MEMORY_MANAGEMENT,
                ProcessCapability.NETWORK_ACCESS,
                ProcessCapability.STORAGE_ACCESS,
                ProcessCapability.PROCESS_MANAGEMENT,
                ProcessCapability.SERVICE_MANAGEMENT,
                ProcessCapability.AGENT_MANAGEMENT,
                ProcessCapability.MESSAGE_BUS_ACCESS,
                ProcessCapability.SYSTEM_MESSAGING,
                ProcessCapability.AGENT_MESSAGING,
                ProcessCapability.MODEL_ACCESS,
                ProcessCapability.SECURITY_POLICY,
                ProcessCapability.CAPABILITY_GRANT
            },
            require_verification=True
        )
        
        # Privileged level policy
        privileged_policy = ProcessIsolationPolicy(
            security_level=SecurityLevel.PRIVILEGED,
            capabilities={
                ProcessCapability.HARDWARE_ACCESS,
                ProcessCapability.NETWORK_ACCESS,
                ProcessCapability.STORAGE_ACCESS,
                ProcessCapability.MESSAGE_BUS_ACCESS,
                ProcessCapability.SYSTEM_MESSAGING,
                ProcessCapability.AGENT_MESSAGING,
                ProcessCapability.MODEL_ACCESS
            },
            memory_limit_mb=4096.0,
            cpu_limit_percent=80.0,
            require_verification=True
        )
        
        # Standard level policy
        standard_policy = ProcessIsolationPolicy(
            security_level=SecurityLevel.STANDARD,
            capabilities={
                ProcessCapability.MESSAGE_BUS_ACCESS,
                ProcessCapability.AGENT_MESSAGING,
                ProcessCapability.USER_DATA_READ,
                ProcessCapability.USER_DATA_WRITE,
                ProcessCapability.MODEL_ACCESS
            },
            memory_limit_mb=2048.0,
            cpu_limit_percent=50.0,
            network_limit_mbps=100.0
        )
        
        # Restricted level policy
        restricted_policy = ProcessIsolationPolicy(
            security_level=SecurityLevel.RESTRICTED,
            capabilities={
                ProcessCapability.MESSAGE_BUS_ACCESS,
                ProcessCapability.USER_DATA_READ
            },
            memory_limit_mb=1024.0,
            cpu_limit_percent=30.0,
            network_limit_mbps=50.0,
            timeout_seconds=300.0
        )
        
        # Sandbox level policy (minimal privileges)
        sandbox_policy = ProcessIsolationPolicy(
            security_level=SecurityLevel.SANDBOX,
            capabilities=set(),  # No capabilities by default
            memory_limit_mb=512.0,
            cpu_limit_percent=10.0,
            network_limit_mbps=0.0,  # No network access
            timeout_seconds=60.0,
            require_verification=False
        )
        
        # Store the default policies
        self.default_policies[SecurityLevel.SYSTEM] = system_policy
        self.default_policies[SecurityLevel.PRIVILEGED] = privileged_policy
        self.default_policies[SecurityLevel.STANDARD] = standard_policy
        self.default_policies[SecurityLevel.RESTRICTED] = restricted_policy
        self.default_policies[SecurityLevel.SANDBOX] = sandbox_policy
    
    def _setup_capability_verifiers(self):
        """Set up verification functions for capabilities."""
        # These functions verify that a process should be granted a capability
        def verify_hardware_access(process_id, metadata):
            # Logic to verify hardware access
            return "hardware_access_key" in metadata
        
        def verify_memory_management(process_id, metadata):
            # Logic to verify memory management
            return metadata.get("is_system_component", False)
        
        def verify_security_policy(process_id, metadata):
            # Logic to verify security policy capability
            return metadata.get("is_security_agent", False)
        
        # Register the verifiers
        self.capability_verifiers[ProcessCapability.HARDWARE_ACCESS] = verify_hardware_access
        self.capability_verifiers[ProcessCapability.MEMORY_MANAGEMENT] = verify_memory_management
        self.capability_verifiers[ProcessCapability.SECURITY_POLICY] = verify_security_policy
        # Additional verifiers would be added for other capabilities
    
    async def _subscribe_to_messages(self):
        """Subscribe to process-related messages on the system bus."""
        system_bus.subscribe(
            "process.create",
            self._handle_process_create,
            "process_isolation_manager"
        )
        
        system_bus.subscribe(
            "process.terminate",
            self._handle_process_terminate,
            "process_isolation_manager"
        )
        
        system_bus.subscribe(
            "process.query",
            self._handle_process_query,
            "process_isolation_manager"
        )
        
        system_bus.subscribe(
            "process.capability.request",
            self._handle_capability_request,
            "process_isolation_manager"
        )
    
    async def _monitor_processes(self):
        """Periodically monitor processes and enforce policies."""
        try:
            while True:
                # Check all running processes
                for process_id, process in list(self.processes.items()):
                    if process.status not in ("terminated", "failed"):
                        # Update resource usage
                        await self._update_process_resources(process)
                        
                        # Check for timeout
                        if process.policy.timeout_seconds:
                            elapsed = time.time() - process.created_at
                            if elapsed > process.policy.timeout_seconds:
                                logger.info(f"Process {process.name} ({process_id}) timed out after {elapsed:.1f} seconds")
                                await self.terminate_process(process_id, reason="timeout")
                        
                        # Check resource limits
                        await self._enforce_resource_limits(process)
                
                # Sleep for a short period (5 seconds)
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            logger.info("Process monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in process monitoring task: {str(e)}", exc_info=True)
    
    async def _update_process_resources(self, process: IsolatedProcess):
        """Update resource usage statistics for a process."""
        # In a real OS, this would get actual resource usage
        # For now, we'll simulate it
        
        if process.process_handle:
            try:
                # Simulate getting resource usage
                process.resource_usage["cpu_percent"] = 10.0 + (hash(process.id) % 20)
                process.resource_usage["memory_mb"] = 100.0 + (hash(process.id) % 500)
                process.resource_usage["network_mbps"] = 5.0 + (hash(process.id) % 15)
                process.last_active = time.time()
            except Exception as e:
                logger.error(f"Error updating resource usage for process {process.id}: {str(e)}")
    
    async def _enforce_resource_limits(self, process: IsolatedProcess):
        """Enforce resource limits on a process."""
        # Check memory limit
        if process.policy.memory_limit_mb and process.resource_usage.get("memory_mb", 0) > process.policy.memory_limit_mb:
            logger.warning(f"Process {process.name} ({process.id}) exceeded memory limit " 
                          f"({process.resource_usage['memory_mb']:.1f}MB > {process.policy.memory_limit_mb:.1f}MB)")
            await self.terminate_process(process.id, reason="memory_limit_exceeded")
        
        # Check CPU limit
        if process.policy.cpu_limit_percent and process.resource_usage.get("cpu_percent", 0) > process.policy.cpu_limit_percent:
            logger.warning(f"Process {process.name} ({process.id}) exceeded CPU limit "
                          f"({process.resource_usage['cpu_percent']:.1f}% > {process.policy.cpu_limit_percent:.1f}%)")
            # For CPU, we might throttle rather than terminate
            # await self.throttle_process(process.id)
        
        # Check network limit
        if process.policy.network_limit_mbps and process.resource_usage.get("network_mbps", 0) > process.policy.network_limit_mbps:
            logger.warning(f"Process {process.name} ({process.id}) exceeded network limit "
                          f"({process.resource_usage['network_mbps']:.1f}Mbps > {process.policy.network_limit_mbps:.1f}Mbps)")
            # We might limit network rather than terminate
            # await self.limit_network(process.id)
    
    async def create_process(self, name: str, owner: str, security_level: SecurityLevel, 
                           metadata: Dict[str, Any] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new isolated process.
        
        Args:
            name: Name of the process
            owner: Owner (component or agent) of the process
            security_level: Security level for the process
            metadata: Additional metadata for the process
            
        Returns:
            Tuple of (success, message, process_id)
        """
        # Generate a unique ID for the process
        process_id = str(uuid.uuid4())
        
        # Get the default policy for this security level
        if security_level not in self.default_policies:
            return False, f"Invalid security level: {security_level}", None
        
        policy = self.default_policies[security_level]
        
        # Create the process object
        process = IsolatedProcess(
            id=process_id,
            name=name,
            owner=owner,
            policy=policy,
            metadata=metadata or {}
        )
        
        # In a real OS, we would create an actual isolated process or container
        # For now, we'll simulate it
        try:
            # Simulate process creation
            process.status = "running"
            process.process_handle = {"simulated": True}
            
            # Store the process
            self.processes[process_id] = process
            
            logger.info(f"Created isolated process {name} ({process_id}) with security level {security_level.name}")
            
            # Emit process creation event
            await system_bus.publish(
                message_type="process.created",
                content={
                    "process_id": process_id,
                    "name": name,
                    "owner": owner,
                    "security_level": security_level.name
                },
                source="process_isolation_manager",
                priority=MessagePriority.NORMAL
            )
            
            return True, f"Created isolated process with ID: {process_id}", process_id
            
        except Exception as e:
            logger.error(f"Error creating isolated process: {str(e)}", exc_info=True)
            return False, f"Error creating process: {str(e)}", None
    
    async def terminate_process(self, process_id: str, reason: str = "requested") -> Tuple[bool, str]:
        """
        Terminate an isolated process.
        
        Args:
            process_id: ID of the process to terminate
            reason: Reason for termination
            
        Returns:
            Tuple of (success, message)
        """
        if process_id not in self.processes:
            return False, f"Process {process_id} not found"
        
        process = self.processes[process_id]
        
        # In a real OS, we would terminate the actual process
        # For now, we'll simulate it
        try:
            # Update process status
            process.status = "terminated"
            process.metadata["termination_reason"] = reason
            
            logger.info(f"Terminated process {process.name} ({process_id}), reason: {reason}")
            
            # Emit process termination event
            await system_bus.publish(
                message_type="process.terminated",
                content={
                    "process_id": process_id,
                    "name": process.name,
                    "owner": process.owner,
                    "reason": reason
                },
                source="process_isolation_manager",
                priority=MessagePriority.NORMAL
            )
            
            return True, f"Terminated process {process_id}"
            
        except Exception as e:
            logger.error(f"Error terminating process {process_id}: {str(e)}", exc_info=True)
            return False, f"Error terminating process: {str(e)}"
    
    async def grant_capability(self, process_id: str, capability: ProcessCapability) -> Tuple[bool, str]:
        """
        Grant a capability to a process.
        
        Args:
            process_id: ID of the process
            capability: Capability to grant
            
        Returns:
            Tuple of (success, message)
        """
        if process_id not in self.processes:
            return False, f"Process {process_id} not found"
        
        process = self.processes[process_id]
        
        # Check if verification is required
        if process.policy.require_verification:
            # Get the verifier for this capability
            verifier = self.capability_verifiers.get(capability)
            if verifier and not verifier(process_id, process.metadata):
                logger.warning(f"Capability verification failed for {capability.name} on process {process_id}")
                return False, f"Capability verification failed for {capability.name}"
        
        # Grant the capability
        process.policy.capabilities.add(capability)
        
        logger.info(f"Granted capability {capability.name} to process {process.name} ({process_id})")
        
        return True, f"Granted capability {capability.name}"
    
    async def check_capability(self, process_id: str, capability: ProcessCapability) -> bool:
        """
        Check if a process has a specific capability.
        
        Args:
            process_id: ID of the process
            capability: Capability to check
            
        Returns:
            True if the process has the capability, False otherwise
        """
        if process_id not in self.processes:
            logger.warning(f"Process {process_id} not found during capability check")
            return False
        
        process = self.processes[process_id]
        return capability in process.policy.capabilities
    
    async def get_process_info(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific process.
        
        Args:
            process_id: ID of the process
            
        Returns:
            Process information dictionary or None if not found
        """
        if process_id not in self.processes:
            return None
        
        process = self.processes[process_id]
        
        return {
            "id": process.id,
            "name": process.name,
            "owner": process.owner,
            "status": process.status,
            "security_level": process.policy.security_level.name,
            "capabilities": [c.name for c in process.policy.capabilities],
            "created_at": process.created_at,
            "last_active": process.last_active,
            "resource_usage": process.resource_usage
        }
    
    async def get_all_processes(self) -> List[Dict[str, Any]]:
        """
        Get information about all processes.
        
        Returns:
            List of process information dictionaries
        """
        return [
            {
                "id": p.id,
                "name": p.name,
                "owner": p.owner,
                "status": p.status,
                "security_level": p.policy.security_level.name
            }
            for p in self.processes.values()
        ]
    
    async def _handle_process_create(self, message):
        """Handle process creation requests from the system bus."""
        content = message.content
        
        success, message_text, process_id = await self.create_process(
            name=content["name"],
            owner=content["owner"],
            security_level=SecurityLevel[content["security_level"]],
            metadata=content.get("metadata", {})
        )
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "message": message_text,
                    "process_id": process_id
                },
                source="process_isolation_manager",
                reply_to=message.source
            )
    
    async def _handle_process_terminate(self, message):
        """Handle process termination requests from the system bus."""
        content = message.content
        
        success, message_text = await self.terminate_process(
            process_id=content["process_id"],
            reason=content.get("reason", "requested")
        )
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "message": message_text
                },
                source="process_isolation_manager",
                reply_to=message.source
            )
    
    async def _handle_process_query(self, message):
        """Handle process query requests from the system bus."""
        content = message.content
        query_type = content.get("type", "all")
        
        result = {}
        
        if query_type == "single":
            # Get info about a specific process
            process_id = content.get("process_id")
            if process_id:
                process_info = await self.get_process_info(process_id)
                if process_info:
                    result["process"] = process_info
                else:
                    result["error"] = f"Process {process_id} not found"
            else:
                result["error"] = "No process_id specified"
                
        elif query_type == "all":
            # Get info about all processes
            processes = await self.get_all_processes()
            result["processes"] = processes
            
        else:
            result["error"] = f"Unknown query type: {query_type}"
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content=result,
                source="process_isolation_manager",
                reply_to=message.source
            )
    
    async def _handle_capability_request(self, message):
        """Handle capability request messages from the system bus."""
        content = message.content
        
        process_id = content["process_id"]
        capability = ProcessCapability[content["capability"]]
        
        success, message_text = await self.grant_capability(process_id, capability)
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": success,
                    "message": message_text
                },
                source="process_isolation_manager",
                reply_to=message.source
            )
    
    async def shutdown(self):
        """Shut down the process isolation manager."""
        logger.info("Shutting down process isolation manager")
        
        # Terminate all processes
        for process_id in list(self.processes.keys()):
            if self.processes[process_id].status not in ("terminated", "failed"):
                await self.terminate_process(process_id, reason="system_shutdown")
        
        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self._initialized = False
        logger.info("Process isolation manager shutdown complete")


# Singleton instance
process_isolation_manager = ProcessIsolationManager()
