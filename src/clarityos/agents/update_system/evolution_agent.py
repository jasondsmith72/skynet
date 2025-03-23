"""
System Evolution Agent for ClarityOS.

This agent is responsible for monitoring, analyzing, and safely updating
the core components of ClarityOS. It enables the system to evolve itself
autonomously while maintaining stability.
"""

import asyncio
import logging
import os
import sys
import time
import json
import re
import importlib
import hashlib
import shutil
from typing import Dict, List, Set, Tuple, Optional, Any, Union

from src.clarityos.core.message_bus import MessagePriority, system_bus
from src.clarityos.agents.update_system.models import (
    UpdatePriority, UpdateStatus, SystemComponent, UpdatePackage
)
from src.clarityos.agents.update_system.utils import compare_versions

# Configure logging
logger = logging.getLogger(__name__)


class SystemEvolutionAgent:
    """
    Agent responsible for evolving the ClarityOS system through updates.
    
    This agent monitors for available updates, validates them, safely applies them,
    tests the updated system, and rolls back if necessary. It enables the OS
    to autonomously improve itself over time.
    """
    
    def __init__(self, agent_id: str, config: Dict):
        """
        Initialize the System Evolution Agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            config: Configuration parameters for the agent
        """
        self.agent_id = agent_id
        self.config = config
        
        # System components registry
        self.components: Dict[str, SystemComponent] = {}
        
        # Available updates
        self.available_updates: Dict[str, UpdatePackage] = {}
        
        # Update history
        self.update_history: List[Dict] = []
        
        # Configuration params
        self.system_root = config.get("system_root", ".")
        self.backup_dir = config.get("backup_dir", os.path.join(self.system_root, "backups"))
        self.update_sources = config.get("update_sources", ["https://clarity-updates.example.com/api/v1/updates"])
        self.auto_update = config.get("auto_update", False)
        self.auto_update_priorities = config.get("auto_update_priorities", [UpdatePriority.CRITICAL])
        self.update_check_interval = config.get("update_check_interval", 86400)  # Default: daily
        self.test_timeout = config.get("test_timeout", 300)  # Default: 5 minutes
        
        # Internal state
        self._shutdown_event = asyncio.Event()
        self._updating = False
        self._subscription_ids = []
    
    async def start(self):
        """Initialize the agent and subscribe to relevant messages."""
        logger.info(f"Starting SystemEvolutionAgent (ID: {self.agent_id})")
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Register message handlers
        self._subscription_ids.append(
            system_bus.subscribe(
                "system.update.check",
                self._handle_update_check,
                f"evolution_agent_{self.agent_id}"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "system.update.apply",
                self._handle_update_apply,
                f"evolution_agent_{self.agent_id}"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "system.component.register",
                self._handle_component_register,
                f"evolution_agent_{self.agent_id}"
            )
        )
        
        # Load system components
        await self._load_components()
        
        # Check for updates on startup if configured
        if self.config.get("check_on_startup", True):
            asyncio.create_task(self._check_for_updates())
        
        # Report initialization complete
        await system_bus.publish(
            message_type="agent.status.update",
            content={
                "agent_id": self.agent_id,
                "status": "running",
                "message": "System Evolution Agent initialized"
            },
            source=f"evolution_agent_{self.agent_id}"
        )
    
    async def stop(self):
        """Clean up and stop the agent."""
        logger.info(f"Stopping SystemEvolutionAgent (ID: {self.agent_id})")
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Unsubscribe from messages
        for subscription_id in self._subscription_ids:
            system_bus.unsubscribe("*", subscription_id)
        
        # Save system component state
        await self._save_components()
        
        # Report shutdown
        await system_bus.publish(
            message_type="agent.status.update",
            content={
                "agent_id": self.agent_id,
                "status": "stopped",
                "message": "System Evolution Agent stopped"
            },
            source=f"evolution_agent_{self.agent_id}"
        )
    
    async def run(self):
        """Main agent loop for periodic update checks."""
        next_check_time = time.time() + self.update_check_interval
        
        while not self._shutdown_event.is_set():
            try:
                current_time = time.time()
                
                # Check for updates if interval has passed
                if current_time >= next_check_time:
                    await self._check_for_updates()
                    next_check_time = current_time + self.update_check_interval
                
                # Apply auto-updates if configured
                await self._process_auto_updates()
                
                # Wait for next cycle or shutdown
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), 60)
                except asyncio.TimeoutError:
                    pass
                
            except Exception as e:
                logger.error(f"Error in SystemEvolutionAgent main loop: {str(e)}", exc_info=True)
                await asyncio.sleep(10.0)  # Wait before retrying
    
    ###########################################
    # Component Management Methods
    ###########################################
    
    async def _load_components(self):
        """Load the registry of system components."""
        try:
            components_file = os.path.join(self.system_root, "components.json")
            if os.path.exists(components_file):
                with open(components_file, 'r') as f:
                    components_data = json.load(f)
                
                for component_data in components_data:
                    self.components[component_data["name"]] = SystemComponent(
                        name=component_data["name"],
                        path=component_data["path"],
                        version=component_data["version"],
                        checksum=component_data["checksum"],
                        dependencies=component_data.get("dependencies", []),
                        last_updated=component_data.get("last_updated", time.time()),
                        update_history=component_data.get("update_history", [])
                    )
                
                logger.info(f"Loaded {len(self.components)} system components")
            else:
                logger.info("No components registry found, will create one")
                # Scan for core components
                await self._scan_for_components()
        
        except Exception as e:
            logger.error(f"Error loading system components: {str(e)}", exc_info=True)
            # Scan for components as fallback
            await self._scan_for_components()
    
    async def _scan_for_components(self):
        """Scan the system directory to discover components."""
        # Core system directories to scan
        core_dirs = [
            os.path.join(self.system_root, "src/clarityos/core"),
            os.path.join(self.system_root, "src/clarityos/agents")
        ]
        
        for directory in core_dirs:
            if not os.path.exists(directory):
                continue
            
            for filename in os.listdir(directory):
                if filename.endswith(".py") and not filename.startswith("__"):
                    filepath = os.path.join(directory, filename)
                    component_name = os.path.splitext(filename)[0]
                    
                    # Generate checksum
                    with open(filepath, 'rb') as f:
                        content = f.read()
                        checksum = hashlib.sha256(content).hexdigest()
                    
                    # Extract version from file if possible
                    version = "0.1.0"  # Default version
                    with open(filepath, 'r') as f:
                        file_content = f.read()
                        version_match = re.search(r'VERSION\s*=\s*[\'"](.+?)[\'"]', file_content)
                        if version_match:
                            version = version_match.group(1)
                    
                    # Extract dependencies if possible
                    dependencies = []
                    import_matches = re.findall(r'from\s+clarityos\.(\w+)\.(\w+)\s+import', file_content)
                    for module_type, module_name in import_matches:
                        if module_name not in dependencies and module_name != component_name:
                            dependencies.append(f"{module_type}.{module_name}")
                    
                    # Create component entry
                    self.components[component_name] = SystemComponent(
                        name=component_name,
                        path=filepath,
                        version=version,
                        checksum=checksum,
                        dependencies=dependencies
                    )
            
            logger.info(f"Scanned {directory}: found {len(self.components)} components")
        
        # Save the components registry
        await self._save_components()
    
    async def _save_components(self):
        """Save the current state of system components to disk."""
        try:
            components_data = []
            for component in self.components.values():
                components_data.append({
                    "name": component.name,
                    "path": component.path,
                    "version": component.version,
                    "checksum": component.checksum,
                    "dependencies": component.dependencies,
                    "last_updated": component.last_updated,
                    "update_history": component.update_history
                })
            
            components_file = os.path.join(self.system_root, "components.json")
            with open(components_file, 'w') as f:
                json.dump(components_data, f, indent=2)
            
            logger.info(f"Saved {len(components_data)} system components")
        
        except Exception as e:
            logger.error(f"Error saving system components: {str(e)}", exc_info=True)
