"""
Base Hardware Interface

This module defines the base class for hardware interfaces in ClarityOS.
"""

import logging
from typing import Dict, Any, Optional, Callable

# Set up logging
logger = logging.getLogger(__name__)

class HardwareInterface:
    """Base class for hardware interfaces."""
    
    def __init__(self, interface_id: str, name: str, description: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the hardware interface.
        
        Args:
            interface_id: Unique identifier for the interface
            name: Human-readable name
            description: Detailed description
            config: Optional configuration parameters
        """
        self.interface_id = interface_id
        self.name = name
        self.description = description
        self.config = config or {}
        self.operations = {}
        self.status = "initialized"
    
    async def initialize(self) -> bool:
        """
        Initialize the hardware interface.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement initialize()")
    
    async def perform_operation(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a hardware operation.
        
        Args:
            operation: Name of the operation to perform
            parameters: Parameters for the operation
            
        Returns:
            Dictionary with operation results
        """
        # Check if operation exists
        if operation not in self.operations:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
                "interface": self.interface_id
            }
        
        # Get the operation handler
        handler = self.operations[operation]
        
        try:
            # Call the handler with the parameters
            result = await handler(parameters)
            
            # Add interface information
            result["interface"] = self.interface_id
            
            return result
        except Exception as e:
            logger.error(f"Error performing operation {operation} on interface {self.interface_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "interface": self.interface_id
            }
    
    def register_operation(self, operation: str, handler: Callable) -> None:
        """
        Register a new operation handler.
        
        Args:
            operation: Name of the operation
            handler: Callable that implements the operation
        """
        self.operations[operation] = handler
        logger.debug(f"Registered operation {operation} on interface {self.interface_id}")
    
    async def close(self) -> None:
        """
        Close the interface and release any resources.
        """
        logger.info(f"Closing interface {self.interface_id}")
        self.status = "closed"
