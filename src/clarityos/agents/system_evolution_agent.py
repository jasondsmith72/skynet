"""
System Evolution Agent for ClarityOS

This agent is responsible for managing the evolution of ClarityOS, including:
- Monitoring for available updates
- Validating updates for security and compatibility
- Applying updates to system components
- Maintaining system version history
- Providing rollback capabilities
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from ..core.agent_base import AgentBase as Agent
from ..core.message_bus import MessageBus
from ..core.priority import Priority

logger = logging.getLogger(__name__)

class SystemEvolutionAgent(Agent):
    """Agent responsible for managing the evolution and updates of ClarityOS."""
    
    def __init__(self, message_bus: MessageBus, config: Optional[Dict] = None):
        super().__init__("system_evolution_agent", message_bus, config)
        
        self.update_sources = {}
        self.component_registry = {}
        self.version_history = []
        self.update_queue = []
        self.current_update = None
        self.update_in_progress = False
        
        # Set up event handlers
        self._register_message_handlers()
        
        logger.info("System Evolution Agent initialized")

    async def start(self):
        """Start the System Evolution Agent and register message handlers."""
        await super().start()
        
        # Start periodic update checks
        self._schedule_update_check()
        
        logger.info("System Evolution Agent started")
        
        # Publish agent status
        await self.message_bus.publish(
            "system/agents/status",
            {
                "agent": "system_evolution_agent",
                "status": "running",
                "capabilities": ["update_management", "version_control", "system_evolution"]
            },
            priority=Priority.STANDARD
        )

    async def stop(self):
        """Stop the System Evolution Agent."""
        logger.info("Stopping System Evolution Agent")
        
        # Cancel any pending update tasks
        if self.update_in_progress:
            await self._cancel_current_update()
        
        await super().stop()
        logger.info("System Evolution Agent stopped")

    def _register_message_handlers(self):
        """Register message handlers for the agent."""
        self.register_handler("system/update/check", self._handle_update_check)
        self.register_handler("system/update/apply", self._handle_apply_update)
        self.register_handler("system/update/rollback", self._handle_rollback)
        self.register_handler("system/component/register", self._handle_component_register)
        self.register_handler("system/restart/completed", self._handle_restart_completed)
        self.register_handler("system/update/status", self._handle_update_status)

    def _schedule_update_check(self):
        """Schedule periodic update checks."""
        check_interval = self.config.get("update_check_interval", 86400)  # Default: once per day
        
        async def scheduled_check():
            while True:
                await asyncio.sleep(check_interval)
                if not self.update_in_progress:
                    await self._check_for_updates()
        
        self.create_task(scheduled_check())
        logger.info(f"Scheduled update checks every {check_interval} seconds")

    async def _handle_update_check(self, message: Dict):
        """Handle manual update check requests."""
        logger.info("Manual update check requested")
        force = message.get("data", {}).get("force", False)
        source = message.get("data", {}).get("source")
        
        updates = await self._check_for_updates(force=force, source=source)
        
        response = {
            "available_updates": updates,
            "update_sources": self.update_sources,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.message_bus.respond(message, response, priority=Priority.HIGH)

    async def _handle_apply_update(self, message: Dict):
        """Handle requests to apply updates."""
        if self.update_in_progress:
            await self.message_bus.respond(
                message,
                {"success": False, "error": "Update already in progress"},
                priority=Priority.HIGH
            )
            return
        
        update_id = message.get("data", {}).get("update_id")
        update = next((u for u in self.update_queue if u.get("id") == update_id), None)
        
        if not update:
            await self.message_bus.respond(
                message,
                {"success": False, "error": f"Update with ID {update_id} not found"},
                priority=Priority.HIGH
            )
            return
        
        # Apply the update
        await self.message_bus.respond(
            message,
            {"success": True, "message": f"Starting update {update_id}"},
            priority=Priority.HIGH
        )
        
        apply_result = await self._apply_update(update)
        
        # Publish the result
        await self.message_bus.publish(
            "system/update/completed",
            {
                "update_id": update_id,
                "success": apply_result["success"],
                "requires_restart": apply_result.get("requires_restart", False),
                "message": apply_result.get("message", ""),
                "timestamp": datetime.utcnow().isoformat()
            },
            priority=Priority.HIGH
        )

    async def _handle_rollback(self, message: Dict):
        """Handle requests to rollback to a previous version."""
        if self.update_in_progress:
            await self.message_bus.respond(
                message,
                {"success": False, "error": "Update in progress, cannot rollback now"},
                priority=Priority.HIGH
            )
            return
        
        version = message.get("data", {}).get("version")
        component = message.get("data", {}).get("component")
        
        # Perform the rollback
        try:
            result = await self._perform_rollback(version, component)
            await self.message_bus.respond(message, result, priority=Priority.HIGH)
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}", exc_info=True)
            await self.message_bus.respond(
                message,
                {"success": False, "error": f"Rollback failed: {str(e)}"},
                priority=Priority.HIGH
            )

    async def _handle_component_register(self, message: Dict):
        """Handle component registration messages."""
        component_data = message.get("data", {})
        if not component_data.get("name"):
            logger.warning("Received component registration without a name")
            return
        
        # Update the component registry
        name = component_data["name"]
        self.component_registry[name] = {
            "name": name,
            "version": component_data.get("version", "0.0.1"),
            "path": component_data.get("path", ""),
            "dependencies": component_data.get("dependencies", []),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Registered component: {name} (version: {component_data.get('version', '0.0.1')})")

    async def _handle_restart_completed(self, message: Dict):
        """Handle restart completed notifications."""
        if self.current_update:
            logger.info("Performing post-restart actions for update")
            await self._perform_post_restart_actions(self.current_update)
            self.update_in_progress = False
            self.current_update = None

    async def _handle_update_status(self, message: Dict):
        """Handle requests for update status information."""
        response = {
            "update_in_progress": self.update_in_progress,
            "current_update": self.current_update,
            "pending_updates": self.update_queue,
            "component_versions": {name: comp["version"] for name, comp in self.component_registry.items()},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.message_bus.respond(message, response, priority=Priority.STANDARD)

    async def _check_for_updates(self, force: bool = False, source: Optional[str] = None) -> List[Dict]:
        """Check for available updates from configured sources."""
        logger.info(f"Checking for updates (force={force}, source={source})")
        # Placeholder implementation
        return []

    async def _apply_update(self, update: Dict) -> Dict:
        """Apply an update to the system."""
        logger.info(f"Applying update: {update['id']}")
        self.update_in_progress = True
        self.current_update = update
        
        try:
            # Determine if this update requires a restart
            requires_restart = update.get("requires_restart", False)
            
            # Apply the update
            result = await self._apply_component_update(update)
            
            if not result["success"]:
                self.update_in_progress = False
                self.current_update = None
                return result
            
            # Handle restart if needed
            if requires_restart:
                await self._initiate_restart(update)
                return {
                    "success": True,
                    "requires_restart": True,
                    "message": "Update applied successfully, restart initiated"
                }
            else:
                self.update_in_progress = False
                self.current_update = None
                return {"success": True, "message": "Update applied successfully"}
                
        except Exception as e:
            logger.error(f"Update failed: {str(e)}", exc_info=True)
            self.update_in_progress = False
            self.current_update = None
            return {"success": False, "error": f"Update failed: {str(e)}"}

    async def _apply_component_update(self, update: Dict) -> Dict:
        """Apply an update to a system component."""
        # Placeholder implementation
        return {"success": True}

    async def _initiate_restart(self, update: Dict) -> None:
        """Initiate a system restart to complete an update."""
        restart_data = {
            "reason": f"Completing update: {update.get('name', update['id'])}",
            "update_id": update["id"]
        }
        
        # In a full implementation, this would call the restart manager
        logger.info(f"Initiating restart for update: {update['id']}")

    async def _perform_post_restart_actions(self, update: Dict) -> None:
        """Perform post-restart actions to complete an update."""
        # Placeholder implementation
        pass

    async def _perform_rollback(self, version: Optional[str], component: Optional[str]) -> Dict:
        """Perform a rollback to a previous version."""
        # Placeholder implementation
        return {"success": True, "message": f"Rollback completed"}

    async def _cancel_current_update(self) -> None:
        """Cancel the current update operation."""
        self.update_in_progress = False
        self.current_update = None
