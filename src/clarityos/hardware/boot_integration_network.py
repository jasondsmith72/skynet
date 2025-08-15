"""
Hardware Boot Integration Network Extension for ClarityOS

This module extends the hardware boot integration to incorporate network functionality,
allowing the AI OS to establish internet connectivity during boot.
"""

import logging
from typing import Dict, Any, Optional

from .boot_integration import HardwareBootIntegration
from .interfaces.network.network_boot_adapter import NetworkBootAdapter
from clarityos.hardware.driver_framework import DriverManager
from clarityos.hardware.hal import HardwareAbstractionLayer
from clarityos.hardware.safety.security_manager import SecurityManager
from clarityos.hardware.knowledge_repository import HardwareKnowledgeRepository as KnowledgeRepository
from clarityos.core.message_bus import MessageBus

# Configure logging
logger = logging.getLogger(__name__)

class HardwareBootNetworkIntegration:
    """
    Extends the hardware boot integration with network capabilities.
    This class ensures network interfaces are properly initialized during boot
    and that the AI system can access the internet to learn and adapt.
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
        self.network_adapter = None
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the Hardware Boot Network Integration."""
        try:
            logger.info("Initializing Hardware Boot Network Integration")
            
            # Create the network adapter
            self.network_adapter = NetworkBootAdapter(
                self.hardware_boot,
                self.message_bus,
                self.driver_manager,
                self.security_manager,
                self.knowledge_repository,
                self.hal
            )
            
            # Initialize the network adapter
            if not await self.network_adapter.initialize():
                logger.error("Failed to initialize Network Boot Adapter")
                return False
            
            # Register boot events for network integration
            self.message_bus.subscribe("system.boot.stage_changed", self._handle_boot_stage_changed)
            self.message_bus.subscribe("system.learning.ready", self._handle_learning_ready)
            
            self._initialized = True
            logger.info("Hardware Boot Network Integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Hardware Boot Network Integration: {e}")
            return False
    
    def _handle_boot_stage_changed(self, message: Dict[str, Any]) -> None:
        """
        Handle boot stage changes to ensure network is initialized at the right time.
        """
        try:
            stage = message.get("stage")
            if not stage:
                return
                
            if stage == "HARDWARE_INIT":
                # Hardware initialization is starting
                logger.info("Hardware initialization stage reached, preparing network subsystem")
                # No action needed yet, just log the progress
                
            elif stage == "HARDWARE_INIT_COMPLETE":
                # Hardware initialization is complete, can start network
                logger.info("Hardware initialization complete, starting network initialization")
                
                # Signal the boot integration that hardware is ready for networking
                self.message_bus.publish("system.boot.hardware_init_complete", {
                    "status": "complete",
                    "hardware_info": message.get("hardware_info", {})
                })
                
        except Exception as e:
            logger.error(f"Error handling boot stage change: {e}")
    
    def _handle_learning_ready(self, message: Dict[str, Any]) -> None:
        """
        Handle the learning subsystem becoming ready.
        This is when we need to ensure internet connectivity is available.
        """
        try:
            if not self._initialized or not self.network_adapter:
                logger.error("Network Boot Integration not properly initialized")
                return
                
            logger.info("Learning subsystem ready, checking internet connectivity")
            
            # Get network status
            network_status = self.network_adapter.get_network_status()
            
            # If internet is connected, notify learning subsystem
            if network_status.get("internet_connected", False):
                logger.info("Internet connectivity available for learning")
                self.message_bus.publish("system.learning.internet_available", {
                    "status": "available",
                    "network_info": network_status.get("network_info", {})
                })
            else:
                logger.warning("Internet connectivity not available for learning")
                # Continue boot process even without internet
                self.message_bus.publish("system.learning.internet_available", {
                    "status": "unavailable",
                    "reason": "No internet connectivity"
                })
                
        except Exception as e:
            logger.error(f"Error handling learning ready event: {e}")
    
    async def shutdown(self) -> None:
        """Shut down the Hardware Boot Network Integration."""
        logger.info("Shutting down Hardware Boot Network Integration")
        
        # Unsubscribe from events
        self.message_bus.unsubscribe("system.boot.stage_changed", self._handle_boot_stage_changed)
        self.message_bus.unsubscribe("system.learning.ready", self._handle_learning_ready)
        
        # Shut down network adapter
        if self.network_adapter:
            await self.network_adapter.shutdown()
            self.network_adapter = None
            
        self._initialized = False
