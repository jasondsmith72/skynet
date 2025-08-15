"""
Network Boot Adapter for ClarityOS

This module provides the connection between the network module and the boot system,
enabling internet access during the boot process.
"""

import logging
from typing import Dict, Any, Optional

from .network_integration import NetworkBootIntegration
from clarityos.hardware.boot_integration import HardwareBootIntegration
from clarityos.hardware.driver_framework import DriverManager
from clarityos.hardware.safety.security_manager import SecurityManager
from clarityos.hardware.knowledge_repository import HardwareKnowledgeRepository as KnowledgeRepository
from clarityos.core.message_bus import MessageBus
from clarityos.hardware.hal import HardwareAbstractionLayer

# Configure logging
logger = logging.getLogger(__name__)

class NetworkBootAdapter:
    """
    Adapter that integrates network functionality into the boot process.
    This class bridges between the main boot system and the network subsystem.
    """
    
    def __init__(self, hardware_boot: HardwareBootIntegration, 
                 message_bus: MessageBus, driver_manager: DriverManager,
                 security_manager: SecurityManager, knowledge_repository: KnowledgeRepository,
                 hal: HardwareAbstractionLayer):
        self.hardware_boot = hardware_boot
        self.message_bus = message_bus
        self.driver_manager = driver_manager
        self.security_manager = security_manager
        self.knowledge_repository = knowledge_repository
        self.hal = hal
        self.network_boot_integration = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the Network Boot Adapter."""
        try:
            logger.info("Initializing Network Boot Adapter")
            
            # Create the network boot integration
            self.network_boot_integration = NetworkBootIntegration(
                self.message_bus,
                self.driver_manager,
                self.security_manager,
                self.knowledge_repository
            )
            
            # Initialize the network boot integration
            if not self.network_boot_integration.initialize():
                logger.error("Failed to initialize Network Boot Integration")
                return False
            
            # Register for boot events
            self.message_bus.subscribe("system.boot.hardware_init_complete", self._handle_hardware_init_complete)
            
            # Signal that we're ready for hardware initialization
            self.message_bus.publish("system.network.boot_adapter_ready", {
                "status": "ready"
            })
            
            self._initialized = True
            logger.info("Network Boot Adapter initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Network Boot Adapter: {e}")
            return False
    
    def _handle_hardware_init_complete(self, message: Dict[str, Any]) -> None:
        """
        Handle the hardware initialization complete event.
        This is when we inform the network boot integration that hardware is ready.
        """
        try:
            if not self._initialized or not self.network_boot_integration:
                logger.error("Network Boot Adapter not properly initialized")
                return
                
            logger.info("Hardware initialization complete, notifying network subsystem")
            
            # Notify network boot integration that hardware initialization is complete
            self.message_bus.publish("system.boot.hardware_init_complete", {
                "status": "complete",
                "hardware_info": message.get("hardware_info", {})
            })
            
        except Exception as e:
            logger.error(f"Error handling hardware init complete: {e}")
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get the current status of the network subsystem during boot."""
        try:
            if not self._initialized or not self.network_boot_integration:
                return {
                    "status": "not_initialized",
                    "error": "Network Boot Adapter not properly initialized"
                }
                
            # If network integration is initialized and has a network manager, get its status
            if hasattr(self.network_boot_integration, "network_manager") and self.network_boot_integration.network_manager:
                net_manager = self.network_boot_integration.network_manager
                return {
                    "status": "ok",
                    "internet_connected": self.network_boot_integration._internet_ready,
                    "network_info": net_manager.get_status() if hasattr(net_manager, "get_status") else {}
                }
            
            # Otherwise, return basic status
            return {
                "status": "initializing",
                "internet_connected": self.network_boot_integration._internet_ready,
                "message": "Network subsystem is still initializing"
            }
            
        except Exception as e:
            logger.error(f"Error getting network status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def shutdown(self) -> None:
        """Shut down the Network Boot Adapter."""
        logger.info("Shutting down Network Boot Adapter")
        
        # Unsubscribe from boot events
        self.message_bus.unsubscribe("system.boot.hardware_init_complete", self._handle_hardware_init_complete)
        
        # Shut down network boot integration
        if self.network_boot_integration:
            self.network_boot_integration.shutdown()
            self.network_boot_integration = None
            
        self._initialized = False
