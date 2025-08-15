"""
Update Manager for ClarityOS.

This module handles the actual update operations for system components, including
backing up, applying updates, testing, and rolling back if necessary.
"""

import asyncio
import logging
import os
import sys
import time
import hashlib
import shutil
import importlib
from typing import Dict, List, Optional, Any, Tuple

from ...core.message_bus import MessagePriority, system_bus
from .models import (
    SystemComponent, UpdatePackage, UpdateStatus
)
from .utils import calculate_file_checksum, create_backup_filename

# Configure logging
logger = logging.getLogger(__name__)


class UpdateManager:
    """
    Handles the actual update operations for system components.
    
    This class is responsible for the mechanics of updating components safely,
    including creating backups, applying updates, testing, and rollback.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the update manager.
        
        Args:
            config: Configuration parameters
        """
        self.config = config
        self.system_root = config.get("system_root", ".")
        self.backup_dir = config.get("backup_dir", os.path.join(self.system_root, "backups"))
        self.test_timeout = config.get("test_timeout", 300)  # Default: 5 minutes
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
    
    async def backup_component(self, component: SystemComponent) -> Optional[str]:
        """
        Create a backup of a component before updating it.
        
        Args:
            component: The component to back up
            
        Returns:
            Path to the backup file, or None if backup failed
        """
        try:
            backup_filename = create_backup_filename(component.name, component.version)
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Copy the file to backup location
            shutil.copy2(component.path, backup_path)
            
            logger.info(f"Created backup of {component.name} at {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Error creating backup for {component.name}: {str(e)}", exc_info=True)
            return None
    
    async def generate_updated_content(self, component: SystemComponent, update: UpdatePackage) -> str:
        """
        Generate updated content for a component.
        
        In a real implementation, this would download and verify the update.
        For this example, we'll simulate by modifying the current file.
        
        Args:
            component: The component to update
            update: The update package
            
        Returns:
            Updated content as string
        """
        with open(component.path, 'r') as f:
            content = f.read()
        
        # Update version number if found
        version_pattern = r'VERSION\s*=\s*[\'"](.+?)[\'"]'
        content = content.replace(f'VERSION = "{component.version}"', f'VERSION = "{update.version}"')
        
        # Insert changelog comment
        changes_comment = "\n# Update changes in version {}:\n".format(update.version)
        for change in update.changes:
            changes_comment += f"# - {change['type']}: {change['description']}\n"
        
        # Find a good place to insert the comment
        import_section_end = content.find("\n\n", content.rfind("import "))
        if import_section_end > 0:
            content = content[:import_section_end] + changes_comment + content[import_section_end:]
        else:
            # If can't find import section, insert at top after any module docstring
            docstring_end = content.find('"""', content.find('"""') + 3)
            if docstring_end > 0:
                insert_pos = content.find("\n", docstring_end) + 1
                content = content[:insert_pos] + changes_comment + content[insert_pos:]
            else:
                # Last resort, add at the top
                content = changes_comment + content
        
        return content
    
    async def test_update(self, component: SystemComponent, update: UpdatePackage) -> Dict:
        """
        Test an applied update to ensure system stability.
        
        Args:
            component: The updated component
            update: The update package
            
        Returns:
            Dictionary with test results
        """
        logger.info(f"Testing update for {component.name}")
        
        try:
            # Load the updated module
            module_path = component.path.replace(os.path.sep, ".").replace(".py", "")
            if module_path.startswith("."):
                module_path = module_path[1:]
            
            # Clear module from cache if already loaded
            if module_path in sys.modules:
                del sys.modules[module_path]
            
            # Try to import the module
            try:
                importlib.import_module(module_path)
            except ImportError as e:
                return {
                    "success": False,
                    "message": f"Failed to import updated module: {str(e)}"
                }
            
            # In a real implementation, would run comprehensive tests here
            # For core components, would restart the system in test mode
            
            # For this example, simply wait a moment to simulate testing
            await asyncio.sleep(1)
            
            return {
                "success": True,
                "message": "Tests passed"
            }
        
        except Exception as e:
            logger.error(f"Error testing update for {component.name}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Test error: {str(e)}"
            }
    
    async def rollback_update(self, component: SystemComponent, backup_path: str) -> bool:
        """
        Roll back an update by restoring from backup.
        
        Args:
            component: The component to roll back
            backup_path: Path to the backup file
            
        Returns:
            True if rollback succeeded, False otherwise
        """
        try:
            logger.info(f"Rolling back update for {component.name}")
            
            # Restore from backup
            shutil.copy2(backup_path, component.path)
            
            logger.info(f"Successfully rolled back {component.name}")
            return True
        
        except Exception as e:
            logger.error(f"Error rolling back update for {component.name}: {str(e)}", exc_info=True)
            return False
    
    async def apply_update(self, component: SystemComponent, update: UpdatePackage) -> Dict:
        """
        Apply an update to a system component.
        
        Args:
            component: The component to update
            update: The update package to apply
            
        Returns:
            Dictionary with update result
        """
        try:
            # 1. Create backup
            backup_path = await self.backup_component(component)
            if not backup_path:
                return {
                    "success": False,
                    "message": f"Failed to create backup for {component.name}"
                }
            
            # 2. Generate updated content
            updated_content = await self.generate_updated_content(component, update)
            
            # 3. Write the updated content
            with open(component.path, 'w') as f:
                f.write(updated_content)
            
            # 4. Test the update
            test_result = await self.test_update(component, update)
            
            if not test_result["success"]:
                # Roll back the update
                logger.error(f"Update test failed for {component.name}: {test_result['message']}")
                rollback_success = await self.rollback_update(component, backup_path)
                
                if rollback_success:
                    return {
                        "success": False,
                        "message": f"Update test failed and was rolled back: {test_result['message']}",
                        "rolled_back": True
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Update test failed and rollback also failed: {test_result['message']}",
                        "rolled_back": False,
                        "critical": True  # Mark as critical issue
                    }
            
            # 5. Update successful
            # Calculate new checksum
            new_checksum = calculate_file_checksum(component.path)
            
            return {
                "success": True,
                "message": f"Successfully updated {component.name} to version {update.version}",
                "new_checksum": new_checksum,
                "old_version": component.version,
                "new_version": update.version
            }
        
        except Exception as e:
            logger.error(f"Error applying update to {component.name}: {str(e)}", exc_info=True)
            
            # Try to roll back if we have a backup
            if backup_path and os.path.exists(backup_path):
                await self.rollback_update(component, backup_path)
            
            return {
                "success": False,
                "message": f"Error applying update: {str(e)}"
            }
