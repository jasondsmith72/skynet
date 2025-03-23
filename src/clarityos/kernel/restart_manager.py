"""
Restart Manager for ClarityOS

This module is responsible for managing system restarts in ClarityOS, including:
- Handling restart requests from various components
- Coordinating graceful shutdown procedures
- Preserving system state across restarts
- Verifying system integrity after restart
"""

import asyncio
import logging
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.clarityos.core.message_bus import MessageBus
from src.clarityos.core.priority import Priority

logger = logging.getLogger(__name__)

class RestartManager:
    """
    Manages system restarts and ensures they happen safely and gracefully.
    """
    
    def __init__(self, message_bus: MessageBus, config: Optional[Dict] = None):
        """Initialize the Restart Manager."""
        self.message_bus = message_bus
        self.config = config or {}
        
        # Directory for storing restart state
        self.state_dir = self.config.get("state_dir", "kernel/restart")
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Restart policies
        self.min_uptime = self.config.get("min_uptime", 60)  # Minimum uptime before allowing restart (seconds)
        self.restart_cooldown = self.config.get("restart_cooldown", 300)  # Minimum time between restarts
        self.max_restarts_per_day = self.config.get("max_restarts_per_day", 5)
        
        # Restart state
        self.restart_history = self._load_restart_history()
        self.pending_restarts = []
        self.restart_in_progress = False
        self.startup_time = time.time()
        self.last_restart_time = self.restart_history[-1]["timestamp"] if self.restart_history else 0
        
        logger.info("Restart Manager initialized")
        
    async def request_restart(self, restart_data: Dict) -> Dict:
        """Request a system restart."""
        logger.info(f"Restart requested: {restart_data.get('reason', 'No reason provided')}")
        
        # Check if restart is allowed
        restart_allowed, restart_error = self._check_restart_policies()
        if not restart_allowed:
            logger.warning(f"Restart denied: {restart_error}")
            return {"success": False, "error": restart_error}
        
        # Set restart type
        restart_type = restart_data.get("restart_type", "full")
        if restart_type not in ["full", "component"]:
            return {"success": False, "error": f"Invalid restart type: {restart_type}"}
        
        # For component restarts, verify components are specified
        if restart_type == "component" and not restart_data.get("components"):
            return {"success": False, "error": "Component restart requested but no components specified"}
        
        # Add the restart request to the queue
        restart_id = f"restart_{int(time.time())}"
        restart_request = {
            "id": restart_id,
            "type": restart_type,
            "reason": restart_data.get("reason", "No reason provided"),
            "components": restart_data.get("components", []),
            "requested_time": time.time(),
            "state": "pending",
            "requester": restart_data.get("requester", "unknown"),
            "preserve_state": restart_data.get("preserve_state", True),
            "related_update": restart_data.get("update_id")
        }
        
        self.pending_restarts.append(restart_request)
        
        # Publish restart request notification
        await self.message_bus.publish(
            "system/restart/requested",
            {
                "restart_id": restart_id,
                "type": restart_type,
                "reason": restart_request["reason"],
                "components": restart_request["components"],
                "timestamp": datetime.utcnow().isoformat()
            },
            priority=Priority.HIGH
        )
        
        # If immediate restart is requested and allowed, initiate it
        if restart_data.get("immediate", False):
            return await self.execute_restart(restart_id)
        
        return {"success": True, "restart_id": restart_id, "message": "Restart request accepted"}
        
    async def execute_restart(self, restart_id: str) -> Dict:
        """Execute a pending restart request."""
        if self.restart_in_progress:
            return {"success": False, "error": "Another restart is already in progress"}
        
        # Find the restart request
        restart_request = next((r for r in self.pending_restarts if r["id"] == restart_id), None)
        if not restart_request:
            return {"success": False, "error": f"Restart request {restart_id} not found"}
        
        # Mark restart as in progress
        self.restart_in_progress = True
        restart_request["state"] = "in_progress"
        
        try:
            # Publish restart initiation notification
            await self.message_bus.publish(
                "system/restart/initiated",
                {
                    "restart_id": restart_id,
                    "type": restart_request["type"],
                    "reason": restart_request["reason"],
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=Priority.CRITICAL
            )
            
            # Save system state if requested
            if restart_request["preserve_state"]:
                await self._save_system_state(restart_request)
            
            # Perform the actual restart
            if restart_request["type"] == "full":
                await self._execute_full_restart(restart_request)
            else:
                await self._execute_component_restart(restart_request)
            
            # The request succeeded if we got here (in a real impl, we'd never reach this point for full restart)
            return {"success": True, "message": "Restart initiated successfully"}
            
        except Exception as e:
            logger.error(f"Restart execution failed: {str(e)}", exc_info=True)
            self.restart_in_progress = False
            restart_request["state"] = "failed"
            
            # Publish restart failure notification
            await self.message_bus.publish(
                "system/restart/failed",
                {
                    "restart_id": restart_id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=Priority.HIGH
            )
            
            return {"success": False, "error": f"Restart execution failed: {str(e)}"}
    
    async def verify_post_restart(self) -> Dict:
        """Verify system integrity after restart and complete the restart process."""
        try:
            # Check if we're recovering from a restart
            restart_state_file = os.path.join(self.state_dir, "pending_restart.json")
            if not os.path.exists(restart_state_file):
                return {"success": True, "message": "No pending restart to complete"}
            
            # Load the restart information
            with open(restart_state_file, "r") as f:
                restart_info = json.load(f)
            
            # Record the restart in history
            self._record_restart_completion(restart_info)
            
            # Restore state if needed
            if restart_info.get("preserve_state", False):
                await self._restore_system_state(restart_info)
            
            # Publish restart completion notification
            await self.message_bus.publish(
                "system/restart/completed",
                {
                    "restart_id": restart_info["id"],
                    "type": restart_info["type"],
                    "reason": restart_info["reason"],
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=Priority.HIGH
            )
            
            # Clean up restart state file
            os.remove(restart_state_file)
            
            return {"success": True, "message": "Post-restart verification completed successfully"}
            
        except Exception as e:
            logger.error(f"Post-restart verification failed: {str(e)}", exc_info=True)
            return {"success": False, "error": f"Post-restart verification failed: {str(e)}"}
    
    def _check_restart_policies(self) -> Tuple[bool, Optional[str]]:
        """Check if a restart is allowed based on configured policies."""
        # Check minimum uptime
        current_uptime = time.time() - self.startup_time
        if current_uptime < self.min_uptime:
            return False, f"System uptime ({current_uptime:.1f}s) is below minimum threshold ({self.min_uptime}s)"
        
        # Check restart cooldown period
        time_since_last_restart = time.time() - self.last_restart_time
        if time_since_last_restart < self.restart_cooldown:
            return False, f"Last restart was too recent ({time_since_last_restart:.1f}s ago, cooldown: {self.restart_cooldown}s)"
        
        # Check maximum restarts per day
        restarts_today = sum(1 for r in self.restart_history 
                           if time.time() - r["timestamp"] < 86400)
        if restarts_today >= self.max_restarts_per_day:
            return False, f"Maximum restarts per day exceeded ({restarts_today}/{self.max_restarts_per_day})"
        
        return True, None
    
    async def _execute_full_restart(self, restart_request: Dict) -> None:
        """Execute a full system restart."""
        logger.info(f"Executing full system restart: {restart_request['reason']}")
        
        # Save pending restart information for recovery after restart
        with open(os.path.join(self.state_dir, "pending_restart.json"), "w") as f:
            json.dump(restart_request, f)
        
        # In a real implementation, this would:
        # 1. Notify all components to prepare for shutdown
        # 2. Wait for all components to acknowledge
        # 3. Perform an actual system restart
        
        # Placeholder implementation - in a real system, we would never reach this point
        logger.info("*** SYSTEM RESTART SIMULATED ***")
        self.restart_in_progress = False
    
    async def _execute_component_restart(self, restart_request: Dict) -> None:
        """Execute a restart of specific components."""
        components = restart_request["components"]
        logger.info(f"Executing component restart for: {', '.join(components)}")
        
        # In a real implementation, this would:
        # 1. Notify the specified components to prepare for restart
        # 2. Wait for all components to acknowledge
        # 3. Stop the components
        # 4. Start the components with new configuration
        
        # For each component, publish restart notification
        for component in components:
            await self.message_bus.publish(
                f"component/{component}/restart",
                {
                    "restart_id": restart_request["id"],
                    "reason": restart_request["reason"],
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=Priority.HIGH
            )
        
        # Wait for acknowledgement (placeholder)
        await asyncio.sleep(1)
        
        # Mark restart as complete
        restart_request["state"] = "completed"
        restart_request["completion_time"] = time.time()
        self.restart_in_progress = False
        
        # Record the restart in history
        self._record_restart_completion(restart_request)
        
        # Publish component restart completion
        await self.message_bus.publish(
            "system/restart/components/completed",
            {
                "restart_id": restart_request["id"],
                "components": components,
                "timestamp": datetime.utcnow().isoformat()
            },
            priority=Priority.HIGH
        )
    
    async def _save_system_state(self, restart_request: Dict) -> None:
        """Save system state before restart for recovery after restart."""
        # Placeholder implementation
        pass
    
    async def _restore_system_state(self, restart_info: Dict) -> None:
        """Restore system state after restart."""
        # Placeholder implementation
        pass
    
    def _record_restart_completion(self, restart_info: Dict) -> None:
        """Record a completed restart in the history."""
        completion_time = time.time()
        
        # Create history entry
        history_entry = {
            "id": restart_info["id"],
            "type": restart_info["type"],
            "reason": restart_info["reason"],
            "components": restart_info.get("components", []),
            "requested_time": restart_info["requested_time"],
            "completion_time": completion_time,
            "timestamp": completion_time,
            "requester": restart_info.get("requester", "unknown"),
            "related_update": restart_info.get("related_update")
        }
        
        # Add to history and save
        self.restart_history.append(history_entry)
        self._save_restart_history()
        
        # Update last restart time
        self.last_restart_time = completion_time
    
    def _load_restart_history(self) -> List[Dict]:
        """Load restart history from storage."""
        history_path = os.path.join(self.state_dir, "restart_history.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load restart history: {str(e)}", exc_info=True)
        
        return []
    
    def _save_restart_history(self) -> None:
        """Save restart history to storage."""
        # Trim history to last 100 entries to prevent unbounded growth
        if len(self.restart_history) > 100:
            self.restart_history = self.restart_history[-100:]
        
        history_path = os.path.join(self.state_dir, "restart_history.json")
        try:
            with open(history_path, "w") as f:
                json.dump(self.restart_history, f)
        except Exception as e:
            logger.error(f"Failed to save restart history: {str(e)}", exc_info=True)
