"""
Memory Safety Monitor

This module implements a safety monitor for memory operations in ClarityOS.
"""

import logging
from typing import Dict, Any, Optional, List

from .base_safety import SafetyMonitor

# Set up logging
logger = logging.getLogger(__name__)

class MemorySafetyMonitor(SafetyMonitor):
    """Safety monitor for memory operations."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            monitor_id="memory_safety",
            name="Memory Safety Monitor",
            description="Ensures safe memory operations",
            config=config
        )
        self.safe_regions = []
        
    async def initialize(self) -> bool:
        """Initialize the memory safety monitor."""
        try:
            # Load safe regions from config
            config_regions = self.config.get("safe_regions", [])
            if config_regions:
                self.safe_regions = config_regions
            else:
                # Define default safe regions
                self.safe_regions = [
                    {"start": 0x1000000, "end": 0x2000000, "flags": "rw", "description": "AI-controlled memory region"},
                    {"start": 0x3000000, "end": 0x4000000, "flags": "r", "description": "Read-only data region"}
                ]
            
            logger.info(f"Initialized memory safety monitor with {len(self.safe_regions)} safe regions")
            return True
        except Exception as e:
            logger.error(f"Error initializing memory safety monitor: {str(e)}")
            return False
    
    def add_safe_region(self, start: int, end: int, flags: str, description: str) -> None:
        """
        Add a new safe memory region.
        
        Args:
            start: Start address of the region
            end: End address of the region
            flags: Access flags ("r", "w", "rw")
            description: Description of the region
        """
        self.safe_regions.append({
            "start": start,
            "end": end,
            "flags": flags,
            "description": description
        })
        logger.info(f"Added safe memory region {start:#x}-{end:#x} ({description})")
    
    def remove_safe_region(self, start: int, end: int) -> bool:
        """
        Remove a safe memory region.
        
        Args:
            start: Start address of the region
            end: End address of the region
            
        Returns:
            True if a region was removed, False otherwise
        """
        for i, region in enumerate(self.safe_regions):
            if region["start"] == start and region["end"] == end:
                del self.safe_regions[i]
                logger.info(f"Removed safe memory region {start:#x}-{end:#x}")
                return True
        
        logger.warning(f"No safe memory region found at {start:#x}-{end:#x}")
        return False
    
    async def check_safety(self, interface_type: str, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check the safety of a memory operation.
        
        Args:
            interface_type: Type of hardware interface
            operation: Operation to perform
            parameters: Parameters for the operation
            
        Returns:
            Dictionary with safety check results
        """
        # Only check memory interface operations
        if interface_type != "memory":
            return {"safe": True}
        
        # For read/write operations, check address range
        if operation in ["read", "write"]:
            if "address" not in parameters:
                return {"safe": False, "reason": "Missing required parameter: address"}
            
            address = parameters["address"]
            size = parameters.get("size", 1)
            end_address = address + size - 1
            
            # Check if the address range is within any safe region
            for region in self.safe_regions:
                if address >= region["start"] and end_address <= region["end"]:
                    # For write operations, check write permission
                    if operation == "write" and "w" not in region["flags"]:
                        return {
                            "safe": False,
                            "reason": f"Write operation not allowed in region {region['start']:#x}-{region['end']:#x} ({region['description']})"
                        }
                    
                    return {"safe": True}
            
            # Address range not in any safe region
            return {
                "safe": False,
                "reason": f"Address range {address:#x}-{end_address:#x} not in any safe region"
            }
        
        # For map/unmap operations, check for appropriate permissions
        if operation == "map":
            # Allow mapping operations for now, but could add additional checks
            return {"safe": True}
        
        if operation == "unmap":
            # Allow unmapping operations for now, but could add additional checks
            return {"safe": True}
        
        # Unknown operation, assume unsafe
        return {
            "safe": False,
            "reason": f"Unknown memory operation: {operation}"
        }
    
    def get_safe_regions(self) -> List[Dict[str, Any]]:
        """
        Get all safe memory regions.
        
        Returns:
            List of safe memory regions
        """
        return self.safe_regions
