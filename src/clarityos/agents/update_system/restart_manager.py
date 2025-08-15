"""
ClarityOS Restart Manager

This module handles graceful system restarts, including restarts for updates,
ensuring proper shutdown and state preservation.
"""

import asyncio
import logging
import os
import sys
import time
import json
import subprocess
from typing import Dict, List, Optional, Any, Union

from ...core.message_bus import MessagePriority, system_bus

# Configure logging
logger = logging.getLogger(__name__)

class RestartManager:
    """
    Manages system restarts and handles restart requests.
    
    The restart manager ensures that restarts are performed gracefully,
    with proper notification and state preservation.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the restart manager.
        
        Args:
            config: Configuration parameters
        """
        self.config = config
        self.system_root = config.get("system_root", ".")
        self.state_dir = config.get("state_dir", os.path.join(self.system_root, "state"))
        self.python_executable = config.get("python_executable", sys.executable)
        self.main_script = config.get("main_script", os.path.join(self.system_root, "run_clarityos.py"))
        self.restart_timeout = config.get("restart_timeout", 60)
        self.pending_restart = None
        self.restart_in_progress = False
        
        # Ensure state directory exists
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Subscription IDs for cleaning up
        self._subscription_ids = []
    
    async def start(self):
        """Start the restart manager."""
        logger.info("Starting restart manager")
        
        # Register message handlers
        self._subscription_ids.append(
            system_bus.subscribe(
                "system.restart.request",
                self._handle_restart_request,
                "restart_manager"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "system.restart.cancel",
                self._handle_restart_cancel,
                "restart_manager"
            )
        )
        
        # Check for restart marker
        await self._check_restart_marker()
    
    async def stop(self):
        """Stop the restart manager."""
        logger.info("Stopping restart manager")
        
        # Unsubscribe from messages
        for subscription_id in self._subscription_ids:
            system_bus.unsubscribe("*", subscription_id)
    
    async def _check_restart_marker(self):
        """Check if this is a restart and handle accordingly."""
        restart_marker_path = os.path.join(self.state_dir, "restart_marker.json")
        
        if os.path.exists(restart_marker_path):
            try:
                with open(restart_marker_path, 'r') as f:
                    restart_info = json.load(f)
                
                # Remove the marker
                os.remove(restart_marker_path)
                
                # Announce the restart completion
                await system_bus.publish(
                    message_type="system.restart.completed",
                    content={
                        "reason": restart_info.get("reason"),
                        "requested_at": restart_info.get("requested_at"),
                        "restart_duration": time.time() - restart_info.get("shutdown_time", 0)
                    },
                    source="restart_manager",
                    priority=MessagePriority.HIGH
                )
                
                logger.info("System restart completed successfully")
                
                # If this was a kernel update restart, check if updates were applied
                if restart_info.get("reason") == "kernel_update":
                    await self._verify_kernel_update(restart_info)
            
            except Exception as e:
                logger.error(f"Error processing restart marker: {str(e)}", exc_info=True)
    
    async def _verify_kernel_update(self, restart_info: Dict):
        """Verify that kernel updates were applied correctly during restart."""
        try:
            # Check for update results
            update_results_path = os.path.join(self.state_dir, "kernel_update_results.json")
            if os.path.exists(update_results_path):
                with open(update_results_path, 'r') as f:
                    update_results = json.load(f)
                
                # Remove the results file
                os.remove(update_results_path)
                
                # Announce results
                await system_bus.publish(
                    message_type="system.kernel.update.results",
                    content=update_results,
                    source="restart_manager",
                    priority=MessagePriority.HIGH
                )
                
                logger.info(f"Kernel update results: {len(update_results['results'])} updates processed")
        
        except Exception as e:
            logger.error(f"Error verifying kernel update: {str(e)}", exc_info=True)
    
    async def _handle_restart_request(self, message):
        """Handle a restart request."""
        if self.restart_in_progress:
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "message": "A restart is already in progress"
                    },
                    source="restart_manager",
                    reply_to=message.source
                )
            return
        
        content = message.content
        reason = content.get("reason", "user_request")
        scheduled_time = content.get("scheduled_time", time.time() + 60)  # Default: 1 minute from now
        urgent = content.get("urgent", False)
        
        # Create restart request
        restart_request = {
            "reason": reason,
            "scheduled_time": scheduled_time,
            "requested_at": time.time(),
            "requested_by": message.source,
            "urgent": urgent,
            "additional_info": {
                key: value for key, value in content.items()
                if key not in ["reason", "scheduled_time", "urgent"]
            }
        }
        
        # Set pending restart
        self.pending_restart = restart_request
        
        # For urgent restarts, start immediately
        if urgent:
            logger.warning(f"Urgent restart requested for reason: {reason}")
            asyncio.create_task(self._perform_restart())
        else:
            # Schedule restart
            delay = max(0, scheduled_time - time.time())
            logger.info(f"Restart scheduled in {delay:.1f} seconds for reason: {reason}")
            
            # Announce scheduled restart
            await system_bus.publish(
                message_type="system.restart.scheduled",
                content={
                    "reason": reason,
                    "scheduled_time": scheduled_time,
                    "delay_seconds": delay
                },
                source="restart_manager",
                priority=MessagePriority.HIGH
            )
            
            # Schedule the restart
            asyncio.create_task(self._schedule_restart(delay))
        
        # Reply if requested
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": True,
                    "message": "Restart scheduled",
                    "scheduled_time": scheduled_time,
                    "urgent": urgent
                },
                source="restart_manager",
                reply_to=message.source
            )
    
    async def _handle_restart_cancel(self, message):
        """Handle a restart cancellation request."""
        if not self.pending_restart or self.restart_in_progress:
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "message": "No pending restart to cancel or restart already in progress"
                    },
                    source="restart_manager",
                    reply_to=message.source
                )
            return
        
        # Cancel the pending restart
        reason = self.pending_restart["reason"]
        self.pending_restart = None
        
        # Announce cancellation
        await system_bus.publish(
            message_type="system.restart.cancelled",
            content={
                "reason": reason
            },
            source="restart_manager",
            priority=MessagePriority.HIGH
        )
        
        logger.info(f"Restart cancelled for reason: {reason}")
        
        # Reply if requested
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content={
                    "success": True,
                    "message": "Restart cancelled"
                },
                source="restart_manager",
                reply_to=message.source
            )
    
    async def _schedule_restart(self, delay: float):
        """
        Schedule a restart after a delay.
        
        Args:
            delay: Delay in seconds before restart
        """
        try:
            # Wait for the specified delay
            await asyncio.sleep(delay)
            
            # Check if restart was cancelled
            if not self.pending_restart:
                logger.info("Scheduled restart was cancelled")
                return
            
            # Perform the restart
            await self._perform_restart()
        
        except asyncio.CancelledError:
            # Task was cancelled
            logger.info("Restart scheduling task was cancelled")
        
        except Exception as e:
            logger.error(f"Error scheduling restart: {str(e)}", exc_info=True)
    
    async def _perform_restart(self):
        """Perform the system restart."""
        if not self.pending_restart:
            logger.warning("No pending restart to perform")
            return
        
        if self.restart_in_progress:
            logger.warning("Restart already in progress")
            return
        
        self.restart_in_progress = True
        restart_info = self.pending_restart
        
        try:
            logger.info(f"Performing system restart for reason: {restart_info['reason']}")
            
            # Announce imminent restart
            await system_bus.publish(
                message_type="system.restart.imminent",
                content={
                    "reason": restart_info["reason"],
                    "time_remaining": 10  # 10 seconds warning
                },
                source="restart_manager",
                priority=MessagePriority.CRITICAL
            )
            
            # Give components time to prepare
            await asyncio.sleep(5)
            
            # Create restart marker
            restart_info["shutdown_time"] = time.time()
            marker_path = os.path.join(self.state_dir, "restart_marker.json")
            with open(marker_path, 'w') as f:
                json.dump(restart_info, f, indent=2)
            
            # Announce final shutdown
            await system_bus.publish(
                message_type="system.shutdown",
                content={
                    "reason": "restart",
                    "restart_info": restart_info
                },
                source="restart_manager",
                priority=MessagePriority.CRITICAL
            )
            
            # Wait for components to shutdown
            await asyncio.sleep(5)
            
            # Spawn the restart process
            logger.info("Spawning restart process")
            restart_cmd = [
                self.python_executable,
                self.main_script,
                "--restart",
                f"--reason={restart_info['reason']}"
            ]
            
            # Use subprocess to start the new process
            subprocess.Popen(
                restart_cmd,
                cwd=self.system_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Exit the current process
            logger.info("Exiting for restart")
            sys.exit(0)
        
        except Exception as e:
            logger.error(f"Error performing restart: {str(e)}", exc_info=True)
            self.restart_in_progress = False
            self.pending_restart = None
            
            # Announce restart failure
            await system_bus.publish(
                message_type="system.restart.failed",
                content={
                    "reason": restart_info["reason"],
                    "error": str(e)
                },
                source="restart_manager",
                priority=MessagePriority.HIGH
            )
