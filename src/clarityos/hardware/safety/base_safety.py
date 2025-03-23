"""
Base Safety Monitor

This module defines the base class for hardware safety monitors in ClarityOS.
"""

import logging
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

class SafetyMonitor:
    """Base class for hardware safety monitors."""
    
    def __init__(self, monitor_id: str, name: str, description: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the safety monitor.
        
        Args:
            monitor_id: Unique identifier for the monitor
            name: Human-readable name
            description: Detailed description
            config: Optional configuration parameters
        """
        self.monitor_id = monitor_id
        self.name = name
        self.description = description
        self.config = config or {}
        self.status = "initialized"
        
    async def initialize(self) -> bool:
        """
        Initialize the safety monitor.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement initialize()")
        
    async def check_safety(self, interface_type: str, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check the safety of a hardware operation.
        
        Args:
            interface_type: Type of hardware interface
            operation: Operation to perform
            parameters: Parameters for the operation
            
        Returns:
            Dictionary with safety check results
        """
        raise NotImplementedError("Subclasses must implement check_safety()")
        
    async def close(self) -> None:
        """
        Close the safety monitor and release any resources.
        """
        logger.info(f"Closing safety monitor {self.monitor_id}")
        self.status = "closed"
