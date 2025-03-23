"""
Process Integration for ClarityOS

This module demonstrates how to integrate the process isolation framework
with existing ClarityOS components, creating secure environments for agents
and services.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from clarityos.core.message_bus import system_bus
from clarityos.core.process_isolation import (
    process_isolation_manager,
    SecurityLevel,
    ProcessCapability
)
from clarityos.core.agent_manager import agent_manager
from clarityos.core.memory_manager import memory_manager

# Configure logging
logger = logging.getLogger(__name__)


class ProcessIntegration:
    """
    Integrates process isolation with ClarityOS components.
    
    This class provides utilities for creating isolated processes for
    agents and services, managing their lifecycle, and enforcing
    capability-based security.
    """
    
    def __init__(self):
        """Initialize the process integration."""
        self.agent_processes: Dict[str, str] = {}  # Map agent_id -> process_id
        self.service_processes: Dict[str, str] = {}  # Map service_name -> process_id
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize the process integration.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        if self._initialized:
            logger.warning("Process integration already initialized")
            return True
        
        logger.info("Initializing process integration")
        
        try:
            # Ensure process isolation manager is initialized
            if not process_isolation_manager._initialized:
                await process_isolation_manager.initialize()
            
            # Subscribe to agent lifecycle messages
            await self._subscribe_to_messages()
            
            self._initialized = True
            logger.info("Process integration initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing process integration: {str(e)}", exc_info=True)
            return False
    
    async def _subscribe_to_messages(self):
        """Subscribe to relevant messages on the system bus."""
        system_bus.subscribe(
            "agent.started",
            self._handle_agent_started,
            "process_integration"
        )
        
        system_bus.subscribe(
            "agent.stopped",
            self._handle_agent_stopped,
            "process_integration"
        )
        
        system_bus.subscribe(
            "service.started",
            self._handle_service_started,
            "process_integration"
        )
        
        system_bus.subscribe(
            "service.stopped",
            self._handle_service_stopped,
            "process_integration"
        )
    
    async def create_agent_process(self, agent_id: str, agent_info: Dict[str, Any]) -> Optional[str]:
        """
        Create an isolated process for an agent.
        
        Args:
            agent_id: ID of the agent
            agent_info: Information about the agent
            
        Returns:
            Process ID if successful, None otherwise
        """
        # Determine the appropriate security level based on agent info
        security_level = self._determine_agent_security_level(agent_info)
        
        # Create metadata for the process
        metadata = {
            "agent_id": agent_id,
            "is_system_component": agent_info.get("is_system_component", False),
            "required_capabilities": agent_info.get("required_capabilities", []),
            "agent_type": agent_info.get("type", "unknown")
        }
        
        # Create the isolated process
        success, message, process_id = await process_isolation_manager.create_process(
            name=f"agent-{agent_info.get('name', agent_id)}",
            owner="agent_manager",
            security_level=security_level,
            metadata=metadata
        )
        
        if success and process_id:
            # Store the mapping
            self.agent_processes[agent_id] = process_id
            
            # Grant required capabilities
            await self._grant_agent_capabilities(process_id, agent_info)
            
            logger.info(f"Created isolated process {process_id} for agent {agent_id}")
            return process_id
        else:
            logger.error(f"Failed to create isolated process for agent {agent_id}: {message}")
            return None
    
    async def terminate_agent_process(self, agent_id: str) -> bool:
        """
        Terminate an agent's isolated process.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            True if successful, False otherwise
        """
        if agent_id not in self.agent_processes:
            logger.warning(f"No isolated process found for agent {agent_id}")
            return False
        
        process_id = self.agent_processes[agent_id]
        
        # Terminate the process
        success, message = await process_isolation_manager.terminate_process(
            process_id=process_id,
            reason="agent_stopped"
        )
        
        if success:
            # Remove the mapping
            del self.agent_processes[agent_id]
            logger.info(f"Terminated isolated process {process_id} for agent {agent_id}")
            return True
        else:
            logger.error(f"Failed to terminate isolated process for agent {agent_id}: {message}")
            return False
    
    def _determine_agent_security_level(self, agent_info: Dict[str, Any]) -> SecurityLevel:
        """Determine the appropriate security level for an agent."""
        agent_type = agent_info.get("type", "").lower()
        
        if agent_info.get("is_system_component", False):
            return SecurityLevel.SYSTEM
        
        if agent_type in ("system", "core", "kernel"):
            return SecurityLevel.PRIVILEGED
        
        if agent_type in ("service", "utility"):
            return SecurityLevel.STANDARD
        
        if agent_info.get("trusted", True):
            return SecurityLevel.STANDARD
        
        return SecurityLevel.RESTRICTED
    
    async def _grant_agent_capabilities(self, process_id: str, agent_info: Dict[str, Any]):
        """Grant required capabilities to an agent's process."""
        required_capabilities = agent_info.get("required_capabilities", [])
        
        for capability_name in required_capabilities:
            try:
                capability = ProcessCapability[capability_name]
                success, message = await process_isolation_manager.grant_capability(
                    process_id=process_id,
                    capability=capability
                )
                
                if success:
                    logger.info(f"Granted capability {capability_name} to process {process_id}")
                else:
                    logger.warning(f"Failed to grant capability {capability_name} to process {process_id}: {message}")
            except KeyError:
                logger.warning(f"Unknown capability: {capability_name}")
    
    async def create_service_process(self, service_name: str, service_info: Dict[str, Any]) -> Optional[str]:
        """
        Create an isolated process for a service.
        
        Args:
            service_name: Name of the service
            service_info: Information about the service
            
        Returns:
            Process ID if successful, None otherwise
        """
        # Determine the appropriate security level based on service info
        security_level = self._determine_service_security_level(service_info)
        
        # Create metadata for the process
        metadata = {
            "service_name": service_name,
            "is_system_service": service_info.get("is_system_service", False),
            "required_capabilities": service_info.get("required_capabilities", []),
            "service_type": service_info.get("type", "unknown")
        }
        
        # Create the isolated process
        success, message, process_id = await process_isolation_manager.create_process(
            name=f"service-{service_name}",
            owner="service_manager",
            security_level=security_level,
            metadata=metadata
        )
        
        if success and process_id:
            # Store the mapping
            self.service_processes[service_name] = process_id
            
            # Grant required capabilities
            await self._grant_service_capabilities(process_id, service_info)
            
            logger.info(f"Created isolated process {process_id} for service {service_name}")
            return process_id
        else:
            logger.error(f"Failed to create isolated process for service {service_name}: {message}")
            return None
    
    async def terminate_service_process(self, service_name: str) -> bool:
        """
        Terminate a service's isolated process.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if successful, False otherwise
        """
        if service_name not in self.service_processes:
            logger.warning(f"No isolated process found for service {service_name}")
            return False
        
        process_id = self.service_processes[service_name]
        
        # Terminate the process
        success, message = await process_isolation_manager.terminate_process(
            process_id=process_id,
            reason="service_stopped"
        )
        
        if success:
            # Remove the mapping
            del self.service_processes[service_name]
            logger.info(f"Terminated isolated process {process_id} for service {service_name}")
            return True
        else:
            logger.error(f"Failed to terminate isolated process for service {service_name}: {message}")
            return False
    
    def _determine_service_security_level(self, service_info: Dict[str, Any]) -> SecurityLevel:
        """Determine the appropriate security level for a service."""
        service_type = service_info.get("type", "").lower()
        
        if service_info.get("is_system_service", False):
            return SecurityLevel.SYSTEM
        
        if service_type in ("core", "kernel", "security"):
            return SecurityLevel.PRIVILEGED
        
        if service_type in ("user", "application"):
            return SecurityLevel.STANDARD
        
        if service_info.get("trusted", True):
            return SecurityLevel.STANDARD
        
        return SecurityLevel.RESTRICTED
    
    async def _grant_service_capabilities(self, process_id: str, service_info: Dict[str, Any]):
        """Grant required capabilities to a service's process."""
        required_capabilities = service_info.get("required_capabilities", [])
        
        for capability_name in required_capabilities:
            try:
                capability = ProcessCapability[capability_name]
                success, message = await process_isolation_manager.grant_capability(
                    process_id=process_id,
                    capability=capability
                )
                
                if success:
                    logger.info(f"Granted capability {capability_name} to process {process_id}")
                else:
                    logger.warning(f"Failed to grant capability {capability_name} to process {process_id}: {message}")
            except KeyError:
                logger.warning(f"Unknown capability: {capability_name}")
    
    async def _handle_agent_started(self, message):
        """Handle agent started messages."""
        content = message.content
        agent_id = content["agent_id"]
        agent_info = content.get("agent_info", {})
        
        # Create an isolated process for the agent
        await self.create_agent_process(agent_id, agent_info)
    
    async def _handle_agent_stopped(self, message):
        """Handle agent stopped messages."""
        content = message.content
        agent_id = content["agent_id"]
        
        # Terminate the agent's process
        await self.terminate_agent_process(agent_id)
    
    async def _handle_service_started(self, message):
        """Handle service started messages."""
        content = message.content
        service_name = content["service_name"]
        service_info = content.get("service_info", {})
        
        # Create an isolated process for the service
        await self.create_service_process(service_name, service_info)
    
    async def _handle_service_stopped(self, message):
        """Handle service stopped messages."""
        content = message.content
        service_name = content["service_name"]
        
        # Terminate the service's process
        await self.terminate_service_process(service_name)
    
    async def get_process_for_agent(self, agent_id: str) -> Optional[str]:
        """Get the process ID for an agent."""
        return self.agent_processes.get(agent_id)
    
    async def get_process_for_service(self, service_name: str) -> Optional[str]:
        """Get the process ID for a service."""
        return self.service_processes.get(service_name)
    
    async def check_agent_capability(self, agent_id: str, capability: ProcessCapability) -> bool:
        """
        Check if an agent's process has a specific capability.
        
        Args:
            agent_id: ID of the agent
            capability: Capability to check
            
        Returns:
            True if the agent has the capability, False otherwise
        """
        process_id = self.agent_processes.get(agent_id)
        if not process_id:
            return False
        
        return await process_isolation_manager.check_capability(process_id, capability)
    
    async def shutdown(self):
        """Shut down the process integration."""
        logger.info("Shutting down process integration")
        
        # Terminate all agent processes
        for agent_id in list(self.agent_processes.keys()):
            await self.terminate_agent_process(agent_id)
        
        # Terminate all service processes
        for service_name in list(self.service_processes.keys()):
            await self.terminate_service_process(service_name)
        
        self._initialized = False
        logger.info("Process integration shutdown complete")


# Singleton instance
process_integration = ProcessIntegration()


# Example usage
async def integrate_with_agents():
    """Example of integrating process isolation with agents."""
    # Initialize the process integration
    await process_integration.initialize()
    
    # Get all running agents
    agent_ids = await agent_manager.get_all_agent_ids()
    
    for agent_id in agent_ids:
        # Get agent info
        agent_info = await agent_manager.get_agent_info(agent_id)
        
        if agent_info:
            # Create a secure process for the agent
            process_id = await process_integration.create_agent_process(agent_id, agent_info)
            
            # Allow the agent to access memory according to its permissions
            if process_id and await process_integration.check_agent_capability(agent_id, ProcessCapability.MEMORY_MANAGEMENT):
                # Example: Grant memory regions to the agent
                memory_request = {
                    "size_mb": 256.0,
                    "type": "USER",
                    "priority": "MEDIUM",
                    "owner": f"agent:{agent_id}"
                }
                
                # In a real implementation, this would interact with the memory manager
                logger.info(f"Would allocate memory for agent {agent_id} in process {process_id}")
