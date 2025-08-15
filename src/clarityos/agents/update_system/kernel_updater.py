"""
ClarityOS Kernel Updater

This module handles the specific complexities of updating the kernel
components safely while the system is running.
"""

import asyncio
import logging
import os
import sys
import time
import json
import importlib
import subprocess
import shutil
from typing import Dict, List, Optional, Any, Union, Tuple

from ...core.message_bus import MessagePriority, system_bus

# Configure logging
logger = logging.getLogger(__name__)

# Define kernel components
KERNEL_COMPONENTS = [
    "message_bus",
    "agent_manager"
]

class KernelUpdater:
    """
    Specialized updater for kernel components of ClarityOS.
    
    The kernel updater handles the delicate process of updating core system
    components while the system is running, ensuring stability and providing
    rollback mechanisms.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the kernel updater.
        
        Args:
            config: Configuration parameters
        """
        self.config = config
        self.system_root = config.get("system_root", ".")
        self.backup_dir = config.get("backup_dir", os.path.join(self.system_root, "backups", "kernel"))
        self.restart_script = config.get("restart_script", "restart_clarityos.py")
        self.safe_mode = config.get("safe_mode", True)
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
    
    async def update_kernel(self, component_name: str, new_version: str, update_file: str) -> Dict:
        """
        Apply an update to a kernel component with special handling.
        
        Args:
            component_name: Name of the kernel component
            new_version: Version to update to
            update_file: Path to the file containing the update
            
        Returns:
            Dictionary with update result
        """
        if component_name not in KERNEL_COMPONENTS:
            return {
                "success": False,
                "message": f"{component_name} is not a recognized kernel component"
            }
        
        logger.info(f"Preparing to update kernel component {component_name} to version {new_version}")
        
        try:
            # 1. Create backup
            component_path = self._get_component_path(component_name)
            if not component_path:
                return {
                    "success": False,
                    "message": f"Could not locate component {component_name}"
                }
            
            backup_path = await self._backup_component(component_name, component_path)
            if not backup_path:
                return {
                    "success": False,
                    "message": f"Failed to create backup for {component_name}"
                }
            
            # 2. Stage update (don't apply directly)
            staging_path = os.path.join(self.backup_dir, f"{component_name}_staged_{new_version}.py")
            with open(update_file, 'rb') as src, open(staging_path, 'wb') as dest:
                dest.write(src.read())
            
            # 3. Create update plan
            update_plan = {
                "component": component_name,
                "current_path": component_path,
                "staging_path": staging_path,
                "backup_path": backup_path,
                "new_version": new_version,
                "timestamp": time.time(),
                "status": "staged"
            }
            
            # Save update plan
            plan_path = os.path.join(self.backup_dir, f"{component_name}_update_plan.json")
            with open(plan_path, 'w') as f:
                json.dump(update_plan, f, indent=2)
            
            # 4. Initiate update
            if self.safe_mode:
                # In safe mode, trigger a restart to apply the update during boot
                await self._request_restart_for_update(update_plan)
                return {
                    "success": True,
                    "message": f"Update for {component_name} staged for application during restart",
                    "restart_required": True
                }
            else:
                # In non-safe mode, try to apply update while running
                result = await self._hot_update_kernel_component(update_plan)
                return result
        
        except Exception as e:
            logger.error(f"Error in kernel update process for {component_name}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Kernel update error: {str(e)}"
            }
    
    def _get_component_path(self, component_name: str) -> Optional[str]:
        """Get the filesystem path for a kernel component."""
        # Standard locations for kernel components
        paths = [
            os.path.join(self.system_root, "src", "clarityos", "core", f"{component_name}.py"),
            os.path.join(self.system_root, "clarityos", "core", f"{component_name}.py")
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
        
        return None
    
    async def _backup_component(self, component_name: str, component_path: str) -> Optional[str]:
        """Create a backup of a kernel component."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{component_name}_backup_{timestamp}.py"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Copy the file to backup location
            with open(component_path, 'rb') as src, open(backup_path, 'wb') as dest:
                dest.write(src.read())
            
            logger.info(f"Created backup of kernel component {component_name} at {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Error creating backup for {component_name}: {str(e)}", exc_info=True)
            return None
    
    async def _request_restart_for_update(self, update_plan: Dict) -> None:
        """Request a system restart to apply the kernel update."""
        await system_bus.publish(
            message_type="system.restart.request",
            content={
                "reason": "kernel_update",
                "component": update_plan["component"],
                "version": update_plan["new_version"],
                "urgent": False,
                "scheduled_time": time.time() + 60  # Give 60 seconds for preparation
            },
            source="kernel_updater",
            priority=MessagePriority.HIGH
        )
        
        logger.info(f"Requested system restart to apply kernel update for {update_plan['component']}")
    
    async def _hot_update_kernel_component(self, update_plan: Dict) -> Dict:
        """
        Attempt to update a kernel component while the system is running.
        
        This is a risky operation and may cause system instability.
        """
        component_name = update_plan["component"]
        logger.warning(f"Attempting hot update of kernel component {component_name} - this may cause instability")
        
        try:
            # 1. Prepare for update
            await system_bus.publish(
                message_type="system.kernel.update.preparing",
                content={
                    "component": component_name,
                    "version": update_plan["new_version"]
                },
                source="kernel_updater",
                priority=MessagePriority.HIGH
            )
            
            # 2. Apply the update
            with open(update_plan["staging_path"], 'rb') as src, open(update_plan["current_path"], 'wb') as dest:
                dest.write(src.read())
            
            # 3. Request reload of the component (where possible)
            await system_bus.publish(
                message_type="system.module.reload",
                content={
                    "module_path": f"src.clarityos.core.{component_name}"
                },
                source="kernel_updater",
                priority=MessagePriority.HIGH
            )
            
            # 4. Update status
            update_plan["status"] = "applied"
            plan_path = os.path.join(self.backup_dir, f"{component_name}_update_plan.json")
            with open(plan_path, 'w') as f:
                json.dump(update_plan, f, indent=2)
            
            # 5. Notify of completion
            await system_bus.publish(
                message_type="system.kernel.update.completed",
                content={
                    "component": component_name,
                    "version": update_plan["new_version"],
                    "restart_recommended": True
                },
                source="kernel_updater",
                priority=MessagePriority.HIGH
            )
            
            return {
                "success": True,
                "message": f"Hot update of kernel component {component_name} completed",
                "restart_recommended": True
            }
        
        except Exception as e:
            logger.error(f"Error during hot update of {component_name}: {str(e)}", exc_info=True)
            await self._rollback_hot_update(update_plan)
            return {
                "success": False,
                "message": f"Hot update failed and was rolled back: {str(e)}"
            }
    
    async def _rollback_hot_update(self, update_plan: Dict) -> None:
        """Roll back a failed hot update."""
        component_name = update_plan["component"]
        logger.info(f"Rolling back hot update for {component_name}")
        
        try:
            # Restore from backup
            with open(update_plan["backup_path"], 'rb') as src, open(update_plan["current_path"], 'wb') as dest:
                dest.write(src.read())
            
            # Update status
            update_plan["status"] = "rolled_back"
            plan_path = os.path.join(self.backup_dir, f"{component_name}_update_plan.json")
            with open(plan_path, 'w') as f:
                json.dump(update_plan, f, indent=2)
            
            # Notify of rollback
            await system_bus.publish(
                message_type="system.kernel.update.rolled_back",
                content={
                    "component": component_name,
                    "reason": "hot_update_failed"
                },
                source="kernel_updater",
                priority=MessagePriority.HIGH
            )
            
            logger.info(f"Successfully rolled back hot update for {component_name}")
        
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to roll back hot update for {component_name}: {str(e)}", exc_info=True)
            # At this point, the system may be in an inconsistent state
            # Request immediate restart
            await system_bus.publish(
                message_type="system.restart.request",
                content={
                    "reason": "rollback_failed",
                    "component": component_name,
                    "urgent": True,
                    "scheduled_time": time.time()  # Immediate restart
                },
                source="kernel_updater",
                priority=MessagePriority.CRITICAL
            )
    
    async def apply_pending_updates(self) -> List[Dict]:
        """
        Apply any pending kernel updates during system startup.
        
        This method should be called during the boot process before
        the core components are fully initialized.
        
        Returns:
            List of results for each update applied
        """
        results = []
        
        # Look for update plans
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.endswith("_update_plan.json"):
                    plan_path = os.path.join(self.backup_dir, filename)
                    
                    with open(plan_path, 'r') as f:
                        update_plan = json.load(f)
                    
                    if update_plan.get("status") == "staged":
                        component_name = update_plan["component"]
                        logger.info(f"Applying staged kernel update for {component_name}")
                        
                        # Apply update
                        try:
                            with open(update_plan["staging_path"], 'rb') as src, open(update_plan["current_path"], 'wb') as dest:
                                dest.write(src.read())
                            
                            # Update status
                            update_plan["status"] = "applied"
                            update_plan["applied_at"] = time.time()
                            with open(plan_path, 'w') as f:
                                json.dump(update_plan, f, indent=2)
                            
                            results.append({
                                "component": component_name,
                                "version": update_plan["new_version"],
                                "success": True
                            })
                            
                            logger.info(f"Successfully applied kernel update for {component_name}")
                        
                        except Exception as e:
                            logger.error(f"Error applying kernel update for {component_name}: {str(e)}", exc_info=True)
                            
                            # Try to rollback
                            try:
                                with open(update_plan["backup_path"], 'rb') as src, open(update_plan["current_path"], 'wb') as dest:
                                    dest.write(src.read())
                                
                                update_plan["status"] = "rolled_back"
                                with open(plan_path, 'w') as f:
                                    json.dump(update_plan, f, indent=2)
                                
                                logger.info(f"Rolled back failed update for {component_name}")
                            
                            except Exception as rollback_error:
                                logger.critical(f"CRITICAL: Failed to rollback kernel update for {component_name}: {str(rollback_error)}")
                            
                            results.append({
                                "component": component_name,
                                "version": update_plan["new_version"],
                                "success": False,
                                "error": str(e)
                            })
        
        except Exception as e:
            logger.error(f"Error checking for pending kernel updates: {str(e)}", exc_info=True)
        
        return results
