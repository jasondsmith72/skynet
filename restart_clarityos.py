#!/usr/bin/env python3
"""
ClarityOS Restart Script

This script is used to restart the ClarityOS system and
apply any pending kernel updates before the main system starts.
"""

import argparse
import logging
import os
import sys
import time
import json
import importlib.util
import subprocess
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('clarity_restart.log')
    ]
)
logger = logging.getLogger("clarity_restart")

def get_project_root():
    """Get the project root directory."""
    # Start from the current file's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Look for markers of the project root
    markers = ["src/clarityos", "requirements.txt", "run_clarityos.py"]
    
    # Start from current directory and go up until we find the project root
    test_dir = current_dir
    while test_dir != os.path.dirname(test_dir):  # Stop at filesystem root
        # Check if this directory contains any of the markers
        if any(os.path.exists(os.path.join(test_dir, marker)) for marker in markers):
            return test_dir
        
        # Go up one directory
        test_dir = os.path.dirname(test_dir)
    
    # If we didn't find the root, use the current directory
    return current_dir


def apply_kernel_updates(project_root: str) -> List[Dict]:
    """
    Apply any pending kernel updates before starting the system.
    
    Args:
        project_root: Path to the project root directory
        
    Returns:
        List of update results
    """
    logger.info("Checking for pending kernel updates")
    
    try:
        # Import the kernel updater module
        kernel_updater_path = os.path.join(project_root, "src/clarityos/agents/update_system/kernel_updater.py")
        if not os.path.exists(kernel_updater_path):
            logger.warning("Kernel updater module not found, skipping updates")
            return []
        
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location("kernel_updater", kernel_updater_path)
        kernel_updater = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kernel_updater)
        
        # Create the kernel updater
        updater = kernel_updater.KernelUpdater({
            "system_root": project_root,
            "backup_dir": os.path.join(project_root, "backups", "kernel")
        })
        
        # Apply pending updates
        # We can't use asyncio here since we're in a standalone script
        # In a real implementation, would need to adapt for async operation
        logger.info("Applying pending kernel updates (synchronous mode)")
        
        # Simulate async operation for this example
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(updater.apply_pending_updates())
        loop.close()
        
        logger.info(f"Applied {len(results)} kernel updates")
        return results
    
    except Exception as e:
        logger.error(f"Error applying kernel updates: {str(e)}", exc_info=True)
        return [{
            "component": "unknown",
            "version": "unknown",
            "success": False,
            "error": str(e)
        }]


def restart_system(project_root: str, reason: str, update_results: List[Dict]):
    """Restart the main ClarityOS process."""
    logger.info(f"Restarting ClarityOS (reason: {reason})")
    
    try:
        # Save update results if any
        if update_results:
            state_dir = os.path.join(project_root, "state")
            os.makedirs(state_dir, exist_ok=True)
            
            results_path = os.path.join(state_dir, "kernel_update_results.json")
            with open(results_path, 'w') as f:
                json.dump({
                    "timestamp": time.time(),
                    "results": update_results
                }, f, indent=2)
        
        # Start the main ClarityOS process
        main_script = os.path.join(project_root, "run_clarityos.py")
        if not os.path.exists(main_script):
            logger.error(f"Main script not found: {main_script}")
            return
        
        logger.info(f"Starting ClarityOS from {main_script}")
        subprocess.run([sys.executable, main_script])
    
    except Exception as e:
        logger.error(f"Error restarting system: {str(e)}", exc_info=True)


def main():
    """Main entry point for restart script."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Restart ClarityOS")
    parser.add_argument("--restart", action="store_true", help="Indicate this is a restart")
    parser.add_argument("--reason", type=str, default="manual", help="Reason for restart")
    args = parser.parse_args()
    
    logger.info(f"ClarityOS restart script starting (reason: {args.reason})")
    
    # Get project root
    project_root = get_project_root()
    logger.info(f"Project root: {project_root}")
    
    # Apply any pending kernel updates
    update_results = apply_kernel_updates(project_root)
    
    # Start the main system
    restart_system(project_root, args.reason, update_results)


if __name__ == "__main__":
    main()
