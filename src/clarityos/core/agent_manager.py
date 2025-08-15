"""
Agent Manager for ClarityOS

This module implements the Agent Manager system which coordinates
all AI agents within ClarityOS, handling their lifecycle, permissions,
and communications.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .message_bus import MessagePriority, system_bus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Possible agent status values."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    UPDATING = "updating"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    FAILED = "failed"


class AgentPermission(Enum):
    """Permission types for agents."""
    # Resource access permissions
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_COMMANDS = "execute_commands"
    NETWORK_ACCESS = "network_access"
    
    # System management permissions
    MANAGE_PROCESSES = "manage_processes"
    MANAGE_USERS = "manage_users"
    MANAGE_SYSTEM = "manage_system"
    MANAGE_AGENTS = "manage_agents"
    
    # Data access permissions
    READ_USER_DATA = "read_user_data"
    WRITE_USER_DATA = "write_user_data"
    READ_SYSTEM_DATA = "read_system_data"
    WRITE_SYSTEM_DATA = "write_system_data"


@dataclass
class AgentCapability:
    """Defines a specific capability an agent provides."""
    id: str
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_permissions: List[AgentPermission] = field(default_factory=list)


@dataclass
class AgentMetrics:
    """Metrics for agent performance and resource usage."""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    request_count: int = 0
    error_count: int = 0
    average_response_time: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class Agent:
    """Represents an AI agent in the system."""
    id: str
    name: str
    version: str
    description: str
    module_path: str
    status: AgentStatus = AgentStatus.INITIALIZING
    capabilities: Dict[str, AgentCapability] = field(default_factory=dict)
    permissions: Set[AgentPermission] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: AgentMetrics = field(default_factory=AgentMetrics)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    subscription_ids: List[str] = field(default_factory=list)
    task: Optional[asyncio.Task] = None


class AgentManager:
    """
    Manages all AI agents within ClarityOS.
    
    This class handles agent registration, lifecycle, permissions,
    and coordinates inter-agent communication.
    """
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.agent_configs_dir = Path("config/agents")
        self.agent_configs_dir.mkdir(parents=True, exist_ok=True)
        self._shutdown_event = asyncio.Event()
        self._running = False
    
    async def start(self) -> None:
        """Start the agent manager and load all configured agents."""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting Agent Manager")
        
        # Subscribe to agent-related messages
        await self._subscribe_to_messages()
        
        # Load agent configurations
        await self._load_agent_configs()
        
        # Start monitoring task
        asyncio.create_task(self._monitor_agents())
        
        logger.info(f"Agent Manager started with {len(self.agents)} agents")
    
    async def stop(self) -> None:
        """Stop the agent manager and all running agents."""
        if not self._running:
            return
        
        logger.info("Stopping Agent Manager")
        self._shutdown_event.set()
        
        # Stop all agents
        stop_tasks = []
        for agent_id in list(self.agents.keys()):
            stop_tasks.append(self.stop_agent(agent_id))
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self._running = False
        logger.info("Agent Manager stopped")
    
    async def _subscribe_to_messages(self) -> None:
        """Subscribe to agent-related messages on the system bus."""
        # Agent lifecycle messages
        system_bus.subscribe(
            "agent.register",
            self._handle_agent_register,
            "agent_manager"
        )
        
        system_bus.subscribe(
            "agent.start",
            self._handle_agent_start,
            "agent_manager"
        )
        
        system_bus.subscribe(
            "agent.stop",
            self._handle_agent_stop,
            "agent_manager"
        )
        
        system_bus.subscribe(
            "agent.update",
            self._handle_agent_update,
            "agent_manager"
        )
        
        # Agent capability discovery
        system_bus.subscribe(
            "agent.capability.discover",
            self._handle_capability_discover,
            "agent_manager"
        )
        
        # Agent status monitoring
        system_bus.subscribe(
            "agent.status.update",
            self._handle_status_update,
            "agent_manager"
        )
    
    async def _load_agent_configs(self) -> None:
        """Load agent configurations from the config directory."""
        if not self.agent_configs_dir.exists():
            logger.warning(f"Agent config directory does not exist: {self.agent_configs_dir}")
            return
        
        for config_file in self.agent_configs_dir.glob("*.json"):
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                
                # Only load agents configured to auto-start
                if config.get("auto_start", False):
                    await self.register_agent(
                        name=config["name"],
                        module_path=config["module_path"],
                        config=config.get("config", {}),
                        auto_start=True
                    )
            except Exception as e:
                logger.error(f"Error loading agent config {config_file}: {str(e)}")
    
    async def _monitor_agents(self) -> None:
        """Periodically monitor agent health and status."""
        while not self._shutdown_event.is_set():
            for agent_id, agent in list(self.agents.items()):
                if agent.status == AgentStatus.RUNNING:
                    # Check if the agent task is still running
                    if agent.task and agent.task.done():
                        try:
                            # Get the exception if any
                            agent.task.result()
                            # No exception, agent terminated normally
                            agent.status = AgentStatus.STOPPED
                        except Exception as e:
                            # Agent failed with exception
                            logger.error(f"Agent {agent.name} failed: {str(e)}")
                            agent.status = AgentStatus.FAILED
                        
                        # Notify about the status change
                        await system_bus.publish(
                            message_type="agent.status.changed",
                            content={
                                "agent_id": agent_id,
                                "status": agent.status.value,
                                "timestamp": time.time()
                            },
                            source="agent_manager",
                            priority=MessagePriority.HIGH
                        )
            
            # Wait for next check
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), 5)
            except asyncio.TimeoutError:
                pass
    
    async def register_agent(
        self,
        name: str,
        module_path: str,
        description: str = "",
        version: str = "0.1.0",
        config: Dict[str, Any] = None,
        permissions: List[AgentPermission] = None,
        auto_start: bool = False
    ) -> Tuple[bool, str]:
        """Register a new agent with the system."""
        # Generate a unique ID for the agent
        agent_id = str(uuid.uuid4())
        
        # Create the agent object
        agent = Agent(
            id=agent_id,
            name=name,
            version=version,
            description=description,
            module_path=module_path,
            status=AgentStatus.INITIALIZING,
            config=config or {},
            permissions=set(permissions or [])
        )
        
        # Store the agent
        self.agents[agent_id] = agent
        
        # Log the registration
        logger.info(f"Registered agent {name} (ID: {agent_id}) from {module_path}")
        
        # Optionally start the agent
        if auto_start:
            success, message = await self.start_agent(agent_id)
            if not success:
                logger.warning(f"Failed to auto-start agent {name}: {message}")
        
        return True, f"Agent {name} registered with ID: {agent_id}"
    
    async def start_agent(self, agent_id: str) -> Tuple[bool, str]:
        """Start a registered agent."""
        if agent_id not in self.agents:
            return False, f"Agent with ID {agent_id} not found"
        
        agent = self.agents[agent_id]
        
        # Check if already running
        if agent.status in (AgentStatus.RUNNING, AgentStatus.INITIALIZING):
            return True, f"Agent {agent.name} is already running or initializing"
        
        # Update status
        agent.status = AgentStatus.INITIALIZING
        
        try:
            # Import the agent module
            module_parts = agent.module_path.split(".")
            module_name = ".".join(module_parts[:-1])
            class_name = module_parts[-1]
            
            try:
                module = __import__(module_name, fromlist=[class_name])
                agent_class = getattr(module, class_name)
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to import agent {agent.name}: {str(e)}")
                agent.status = AgentStatus.FAILED
                return False, f"Failed to import agent module: {str(e)}"
            
            # Create agent instance and start it
            agent_instance = agent_class(agent_id, agent.config)
            
            # Create task for agent's run method
            agent.task = asyncio.create_task(self._run_agent(agent_id, agent_instance))
            
            logger.info(f"Started agent {agent.name} (ID: {agent_id})")
            return True, f"Agent {agent.name} started"
            
        except Exception as e:
            logger.error(f"Error starting agent {agent.name}: {str(e)}", exc_info=True)
            agent.status = AgentStatus.FAILED
            return False, f"Error starting agent: {str(e)}"
    
    async def _run_agent(self, agent_id: str, agent_instance: Any) -> None:
        """Run an agent in a dedicated task."""
        agent = self.agents[agent_id]
        
        try:
            # Call the agent's start method
            if hasattr(agent_instance, "start"):
                await agent_instance.start()
            
            # Update status
            agent.status = AgentStatus.RUNNING
            
            # Call the agent's run method (should be long-running)
            if hasattr(agent_instance, "run"):
                await agent_instance.run()
            else:
                # If no run method, just keep the agent alive
                while not self._shutdown_event.is_set():
                    await asyncio.sleep(1)
            
            # If we get here, the agent terminated normally
            agent.status = AgentStatus.STOPPED
            
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            logger.info(f"Agent {agent.name} task cancelled")
            
            if hasattr(agent_instance, "stop"):
                try:
                    await agent_instance.stop()
                except Exception as e:
                    logger.error(f"Error stopping agent {agent.name}: {str(e)}")
            
            agent.status = AgentStatus.STOPPED
            
        except Exception as e:
            # Agent failed with exception
            logger.error(f"Agent {agent.name} failed: {str(e)}", exc_info=True)
            agent.status = AgentStatus.FAILED
    
    async def stop_agent(self, agent_id: str) -> Tuple[bool, str]:
        """Stop a running agent."""
        if agent_id not in self.agents:
            return False, f"Agent with ID {agent_id} not found"
        
        agent = self.agents[agent_id]
        
        # Check if already stopped
        if agent.status in (AgentStatus.STOPPED, AgentStatus.FAILED):
            return True, f"Agent {agent.name} is already stopped"
        
        # Update status
        agent.status = AgentStatus.STOPPED
        
        # Cancel the agent task
        if agent.task and not agent.task.done():
            agent.task.cancel()
            try:
                await agent.task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Stopped agent {agent.name} (ID: {agent_id})")
        return True, f"Agent {agent.name} stopped"
    
    # Message handlers
    
    async def _handle_agent_register(self, message):
        """Handle agent registration requests."""
        content = message.content
        success, result = await self.register_agent(
            name=content["name"],
            module_path=content["module_path"],
            description=content.get("description", ""),
            version=content.get("version", "0.1.0"),
            config=content.get("config", {}),
            permissions=[AgentPermission(p) for p in content.get("permissions", [])],
            auto_start=content.get("auto_start", False)
        )
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={"success": success, "message": result},
                source="agent_manager",
                reply_to=message.source
            )
    
    async def _handle_agent_start(self, message):
        """Handle agent start requests."""
        content = message.content
        success, result = await self.start_agent(content["agent_id"])
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={"success": success, "message": result},
                source="agent_manager",
                reply_to=message.source
            )
    
    async def _handle_agent_stop(self, message):
        """Handle agent stop requests."""
        content = message.content
        success, result = await self.stop_agent(content["agent_id"])
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={"success": success, "message": result},
                source="agent_manager",
                reply_to=message.source
            )
    
    async def _handle_agent_update(self, message):
        """Handle agent update requests."""
        content = message.content
        agent_id = content["agent_id"]
        
        if agent_id not in self.agents:
            result = {"success": False, "message": f"Agent with ID {agent_id} not found"}
        else:
            # Update agent configuration
            agent = self.agents[agent_id]
            
            if "config" in content:
                agent.config.update(content["config"])
            
            if "version" in content:
                agent.version = content["version"]
            
            agent.last_updated = time.time()
            
            # Restart if requested
            if content.get("restart", False):
                await self.stop_agent(agent_id)
                success, message = await self.start_agent(agent_id)
                result = {"success": success, "message": message}
            else:
                result = {"success": True, "message": f"Agent {agent.name} updated"}
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content=result,
                source="agent_manager",
                reply_to=message.source
            )
    
    async def _handle_capability_discover(self, message):
        """Handle capability discovery requests."""
        content = message.content
        
        # If agent_id specified, get capabilities for just that agent
        if "agent_id" in content:
            agent_id = content["agent_id"]
            if agent_id not in self.agents:
                result = {"success": False, "message": f"Agent with ID {agent_id} not found"}
            else:
                agent = self.agents[agent_id]
                result = {
                    "success": True,
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "capabilities": {
                        cap_id: {
                            "id": cap.id,
                            "name": cap.name,
                            "description": cap.description,
                            "parameters": cap.parameters
                        }
                        for cap_id, cap in agent.capabilities.items()
                    }
                }
        else:
            # Get capabilities for all agents
            result = {
                "success": True,
                "agents": {
                    agent_id: {
                        "name": agent.name,
                        "capabilities": {
                            cap_id: {
                                "id": cap.id,
                                "name": cap.name,
                                "description": cap.description,
                                "parameters": cap.parameters
                            }
                            for cap_id, cap in agent.capabilities.items()
                        }
                    }
                    for agent_id, agent in self.agents.items()
                }
            }
        
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content=result,
                source="agent_manager",
                reply_to=message.source
            )
    
    async def _handle_status_update(self, message):
        """Handle agent status update reports."""
        content = message.content
        agent_id = content["agent_id"]
        
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            
            # Update metrics
            if "metrics" in content:
                metrics = content["metrics"]
                agent.metrics.cpu_usage = metrics.get("cpu_usage", agent.metrics.cpu_usage)
                agent.metrics.memory_usage = metrics.get("memory_usage", agent.metrics.memory_usage)
                agent.metrics.request_count = metrics.get("request_count", agent.metrics.request_count)
                agent.metrics.error_count = metrics.get("error_count", agent.metrics.error_count)
                agent.metrics.average_response_time = metrics.get("average_response_time", agent.metrics.average_response_time)
                agent.metrics.last_updated = time.time()
            
            # Update status if provided
            if "status" in content:
                try:
                    new_status = AgentStatus(content["status"])
                    
                    # Only log if status changed
                    if agent.status != new_status:
                        logger.info(f"Agent {agent.name} status changed: {agent.status.value} -> {new_status.value}")
                        
                        # Update status
                        agent.status = new_status
                        
                        # Broadcast status change
                        await system_bus.publish(
                            message_type="agent.status.changed",
                            content={
                                "agent_id": agent_id,
                                "status": new_status.value,
                                "timestamp": time.time()
                            },
                            source="agent_manager",
                            priority=MessagePriority.NORMAL
                        )
                    
                except ValueError:
                    logger.warning(f"Invalid agent status: {content['status']}")


# Singleton instance
agent_manager = AgentManager()
