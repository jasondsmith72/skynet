"""
Kernel Updater for ClarityOS

This module is responsible for safely updating kernel components of ClarityOS,
which include critical system components such as:
- Message Bus
- Agent Manager
- Memory Management
- Hardware Interfaces

It provides two update strategies:
1. Hot update - Update components without system restart
2. Restart-based update - Stage updates to be applied during system restart
"""

import asyncio
import logging
import os
import shutil
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.clarityos.core.message_bus import MessageBus
from src.clarityos.core.priority import Priority

logger = logging.getLogger(__name__)

class KernelUpdater:
    """
    Handles safe updates to critical kernel components in ClarityOS.
    
    This class provides mechanisms for updating core system components
    either through hot updates (without restart) or through staged updates
    that are applied during system restart.
    """
    
    def __init__(self, message_bus: MessageBus, config: Optional[Dict] = None):
        """
        Initialize the Kernel Updater.
        
        Args:
            message_bus: The system message bus
            config: Optional configuration dictionary
        """
        self.message_bus = message_bus
        self.config = config or {}
        
        # Directory for staging updates that will be applied during restart
        self.staged_updates_dir = self.config.get("staged_updates_dir", "kernel/updates/staged")
        
        # Directory for backups of kernel components
        self.backup_dir = self.config.get("backup_dir", "kernel/backups")
        
        # Critical components that require special handling
        self.critical_components = self.config.get("critical_components", [
            "message_bus",
            "agent_manager",
            "memory_manager",
            "hardware_interface"
        ])
        
        # Initialize the staging directory
        os.makedirs(self.staged_updates_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logger.info("Kernel Updater initialized")

    async def apply_update(self, update: Dict) -> Dict:
        """
        Apply an update to kernel components.
        
        Args:
            update: The update to apply
            
        Returns:
            A dictionary with the result of the operation
        """
        logger.info(f"Applying kernel update: {update['id']}")
        
        # Determine if this is a critical component that needs special handling
        component = update.get("component")
        is_critical = component in self.critical_components
        
        # Check update strategy based on component type and update parameters
        update_strategy = self._determine_update_strategy(update)
        
        if update_strategy == "hot_update":
            return await self._apply_hot_update(update)
        elif update_strategy == "staged_update":
            return await self._stage_update_for_restart(update)
        else:
            return {
                "success": False, 
                "error": f"Invalid update strategy: {update_strategy}"
            }

    def _determine_update_strategy(self, update: Dict) -> str:
        """
        Determine the appropriate update strategy for a kernel component.
        
        Args:
            update: The update to apply
            
        Returns:
            The update strategy: "hot_update" or "staged_update"
        """
        component = update.get("component")
        force_restart = update.get("force_restart", False)
        allows_hot_update = update.get("allows_hot_update", False)
        
        # Critical components generally require restart
        if component in self.critical_components and not allows_hot_update:
            return "staged_update"
        
        # If the update forces a restart, use staged update
        if force_restart:
            return "staged_update"
            
        # Otherwise, we can do a hot update
        return "hot_update"

    async def _apply_hot_update(self, update: Dict) -> Dict:
        """
        Apply an update to a kernel component without restart.
        
        Args:
            update: The update to apply
            
        Returns:
            A dictionary with the result of the operation
        """
        logger.info(f"Applying hot update to kernel component: {update.get('component')}")
        
        try:
            # Create a backup before updating
            backup_result = await self._create_backup(update)
            if not backup_result["success"]:
                return backup_result
            
            # In a real implementation, this would:
            # 1. Load the new component code
            # 2. Safely swap out the old implementation
            # 3. Validate the new implementation
            
            # For now, we'll simulate a successful hot update
            await asyncio.sleep(1)  # Simulate update operation
            
            # Publish update notification
            await self.message_bus.publish(
                "kernel/component/updated",
                {
                    "component": update.get("component"),
                    "version": update.get("version"),
                    "update_id": update["id"],
                    "restart_required": False,
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=Priority.HIGH
            )
            
            return {"success": True, "message": "Hot update applied successfully"}
            
        except Exception as e:
            logger.error(f"Hot update failed: {str(e)}", exc_info=True)
            
            # Try to restore from backup
            try:
                await self._restore_backup(update)
            except Exception as restore_error:
                logger.error(f"Backup restoration also failed: {str(restore_error)}", exc_info=True)
            
            return {"success": False, "error": f"Hot update failed: {str(e)}"}

    async def _stage_update_for_restart(self, update: Dict) -> Dict:
        """
        Stage an update to be applied during system restart.
        
        Args:
            update: The update to stage
            
        Returns:
            A dictionary with the result of the operation
        """
        logger.info(f"Staging update for restart: {update['id']}")
        
        try:
            # Create a unique staging directory for this update
            staging_dir = os.path.join(
                self.staged_updates_dir, 
                f"{update.get('component', 'unknown')}_{update['id']}"
            )
            os.makedirs(staging_dir, exist_ok=True)
            
            # Save update information
            with open(os.path.join(staging_dir, "update_info.json"), "w") as f:
                json.dump({
                    "id": update["id"],
                    "component": update.get("component"),
                    "version": update.get("version"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "requires_restart": True
                }, f)
            
            # In a real implementation, this would:
            # 1. Extract the update files to the staging directory
            # 2. Validate the staged files
            # 3. Create scripts to apply the update during restart
            
            # Publish staged update notification
            await self.message_bus.publish(
                "kernel/update/staged",
                {
                    "update_id": update["id"],
                    "component": update.get("component"),
                    "version": update.get("version"),
                    "staging_dir": staging_dir,
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=Priority.HIGH
            )
            
            return {
                "success": True, 
                "requires_restart": True,
                "message": "Update staged for next system restart"
            }
            
        except Exception as e:
            logger.error(f"Failed to stage update: {str(e)}", exc_info=True)
            return {"success": False, "error": f"Failed to stage update: {str(e)}"}

    async def _create_backup(self, update: Dict) -> Dict:
        """
        Create a backup of a kernel component before updating.
        
        Args:
            update: The update being applied
            
        Returns:
            A dictionary with the backup result
        """
        component = update.get("component")
        if not component:
            return {"success": False, "error": "No component specified for backup"}
        
        try:
            # Create a unique backup directory
            backup_id = f"{component}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            backup_path = os.path.join(self.backup_dir, backup_id)
            os.makedirs(backup_path, exist_ok=True)
            
            # In a real implementation, this would:
            # 1. Copy the component files to the backup directory
            # 2. Save component state if applicable
            # 3. Record backup metadata
            
            # Save backup information
            with open(os.path.join(backup_path, "backup_info.json"), "w") as f:
                json.dump({
                    "component": component,
                    "version": update.get("version_from"),
                    "update_id": update["id"],
                    "timestamp": datetime.utcnow().isoformat()
                }, f)
                
            # Add backup info to the update
            update["backup_path"] = backup_path
            
            return {"success": True, "backup_path": backup_path}
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}", exc_info=True)
            return {"success": False, "error": f"Backup failed: {str(e)}"}

    async def _restore_backup(self, update: Dict) -> Dict:
        """
        Restore a kernel component from backup after a failed update.
        
        Args:
            update: The update that failed
            
        Returns:
            A dictionary with the restore result
        """
        backup_path = update.get("backup_path")
        if not backup_path:
            return {"success": False, "error": "No backup path specified for restoration"}
        
        try:
            # In a real implementation, this would:
            # 1. Stop the updated component if it's running
            # 2. Restore files from backup
            # 3. Restart the component
            
            # Publish restoration notification
            await self.message_bus.publish(
                "kernel/component/restored",
                {
                    "component": update.get("component"),
                    "update_id": update["id"],
                    "backup_path": backup_path,
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=Priority.HIGH
            )
            
            return {"success": True, "message": "Restoration from backup successful"}
            
        except Exception as e:
            logger.error(f"Restoration failed: {str(e)}", exc_info=True)
            return {
                "success": False, 
                "error": f"Restoration failed: {str(e)}",
                "critical": True  # Mark as critical since we failed to restore
            }

    async def apply_staged_updates(self) -> Dict:
        """
        Apply updates that were staged for system restart.
        
        This method is called during system boot to apply any updates
        that were staged before the restart.
        
        Returns:
            A dictionary with the result of the operation
        """
        logger.info("Applying staged kernel updates")
        
        try:
            # Find all staged updates
            staged_updates = []
            for item in os.listdir(self.staged_updates_dir):
                item_path = os.path.join(self.staged_updates_dir, item)
                if os.path.isdir(item_path):
                    info_path = os.path.join(item_path, "update_info.json")
                    if os.path.exists(info_path):
                        with open(info_path, "r") as f:
                            update_info = json.load(f)
                            update_info["staging_dir"] = item_path
                            staged_updates.append(update_info)
            
            if not staged_updates:
                logger.info("No staged updates found")
                return {"success": True, "message": "No staged updates to apply"}
            
            # Apply each staged update
            results = []
            for update in staged_updates:
                try:
                    # In a real implementation, this would:
                    # 1. Extract the staged files
                    # 2. Replace the existing component files
                    # 3. Update component configuration
                    
                    # Simulate update application
                    await asyncio.sleep(1)
                    
                    # Publish update application notification
                    await self.message_bus.publish(
                        "kernel/update/applied",
                        {
                            "update_id": update["id"],
                            "component": update.get("component"),
                            "version": update.get("version"),
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        priority=Priority.HIGH
                    )
                    
                    # Clean up the staging directory
                    shutil.rmtree(update["staging_dir"], ignore_errors=True)
                    
                    results.append({
                        "update_id": update["id"],
                        "component": update.get("component"),
                        "success": True
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to apply staged update {update['id']}: {str(e)}", exc_info=True)
                    results.append({
                        "update_id": update["id"],
                        "component": update.get("component"),
                        "success": False,
                        "error": str(e)
                    })
            
            # Summarize results
            success_count = sum(1 for r in results if r["success"])
            total_count = len(results)
            
            return {
                "success": success_count == total_count,
                "message": f"Applied {success_count}/{total_count} staged updates",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Failed to apply staged updates: {str(e)}", exc_info=True)
            return {"success": False, "error": f"Failed to apply staged updates: {str(e)}"}
