"""
Network Integration for ClarityOS Boot Process

This module integrates network connectivity into the ClarityOS boot process,
ensuring safe internet access is available for the AI system to learn and adapt.
"""

import logging
import threading
from typing import Dict, Any, Optional

from .network_manager import NetworkManager
from ...driver_framework import DriverManager
from ...safety.security_manager import SecurityManager
from ...knowledge_repository import HardwareKnowledgeRepository as KnowledgeRepository
from clarityos.core.message_bus import MessageBus

# Configure logging
logger = logging.getLogger(__name__)

class NetworkBootIntegration:
    """
    Integrates network connectivity into the ClarityOS boot process.
    This class ensures safe network drivers are loaded and configured
    to provide internet access during system boot.
    """
    
    def __init__(self, message_bus: MessageBus, driver_manager: DriverManager,
                 security_manager: SecurityManager, knowledge_repository: KnowledgeRepository):
        self.message_bus = message_bus
        self.driver_manager = driver_manager
        self.security_manager = security_manager
        self.knowledge_repository = knowledge_repository
        self.network_manager = None
        self._internet_ready = False
        self._boot_complete = False
        
    def initialize(self) -> bool:
        """Initialize the Network Boot Integration."""
        try:
            logger.info("Initializing Network Boot Integration")
            
            # Subscribe to relevant boot messages
            self.message_bus.subscribe("system.boot.hardware_init_complete", self._handle_hardware_init_complete)
            self.message_bus.subscribe("system.boot.complete", self._handle_boot_complete)
            self.message_bus.subscribe("system.network.internet_status_changed", self._handle_internet_status_changed)
            
            logger.info("Network Boot Integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Network Boot Integration: {e}")
            return False
    
    def _handle_hardware_init_complete(self, message: Dict[str, Any]) -> None:
        """
        Handle the hardware initialization complete event.
        This is when we should initialize network connectivity.
        """
        try:
            logger.info("Hardware initialization complete, starting network setup")
            
            # Initialize network manager
            self.network_manager = NetworkManager(
                self.message_bus,
                self.driver_manager,
                self.security_manager,
                self.knowledge_repository
            )
            
            # Initialize network hardware
            if not self.network_manager.initialize():
                logger.error("Failed to initialize network manager")
                self.message_bus.publish("system.network.boot_status", {
                    "status": "error",
                    "message": "Failed to initialize network manager"
                })
                return
            
            # Try to establish network connectivity
            self._establish_connectivity()
            
        except Exception as e:
            logger.error(f"Error handling hardware init complete: {e}")
            self.message_bus.publish("system.network.boot_status", {
                "status": "error",
                "message": f"Error during network setup: {e}"
            })
    
    def _establish_connectivity(self) -> None:
        """
        Attempt to establish network connectivity.
        This is done in a separate thread to avoid blocking the boot process.
        """
        # Create a thread to establish connectivity
        connectivity_thread = threading.Thread(
            target=self._connectivity_thread,
            daemon=True
        )
        connectivity_thread.start()
    
    def _connectivity_thread(self) -> None:
        """Background thread to establish network connectivity."""
        try:
            logger.info("Attempting to establish network connectivity...")
            
            # Update boot status
            self.message_bus.publish("system.network.boot_status", {
                "status": "connecting",
                "message": "Attempting to establish network connectivity"
            })
            
            # Try to connect to the best available network
            success = self.network_manager.connect_best_interface(timeout=60)
            
            if not success:
                logger.warning("Failed to automatically connect, continuing boot process")
                self.message_bus.publish("system.network.boot_status", {
                    "status": "warning",
                    "message": "Automatic network connection failed, continuing boot process"
                })
                return
                
            logger.info("Successfully established network connectivity")
            self.message_bus.publish("system.network.boot_status", {
                "status": "connected",
                "message": "Network connectivity established"
            })
            
            # Internet status will be updated by the network manager
            
        except Exception as e:
            logger.error(f"Error establishing network connectivity: {e}")
            self.message_bus.publish("system.network.boot_status", {
                "status": "error",
                "message": f"Error establishing network connectivity: {e}"
            })
    
    def _handle_internet_status_changed(self, message: Dict[str, Any]) -> None:
        """Handle changes in internet connectivity status."""
        internet_connected = message.get("connected", False)
        self._internet_ready = internet_connected
        
        if internet_connected:
            logger.info("Internet connectivity established")
            self.message_bus.publish("system.network.boot_status", {
                "status": "internet_connected",
                "message": "Internet connectivity established"
            })
            
            # If boot is already complete, notify the learning subsystems
            if self._boot_complete:
                self._notify_learning_subsystems()
        else:
            logger.warning("Internet connectivity lost")
            self.message_bus.publish("system.network.boot_status", {
                "status": "internet_disconnected",
                "message": "Internet connectivity lost"
            })
    
    def _handle_boot_complete(self, message: Dict[str, Any]) -> None:
        """
        Handle the boot complete event.
        At this point, we should notify learning subsystems if internet is available.
        """
        self._boot_complete = True
        
        if self._internet_ready:
            self._notify_learning_subsystems()
    
    def _notify_learning_subsystems(self) -> None:
        """
        Notify learning subsystems that internet access is available.
        This allows the AI to begin learning from online resources.
        """
        logger.info("Notifying learning subsystems about internet availability")
        
        self.message_bus.publish("system.learning.internet_available", {
            "status": "available",
            "network_info": self.network_manager.get_status() if self.network_manager else {}
        })
    
    def shutdown(self) -> None:
        """Shut down the Network Boot Integration."""
        logger.info("Shutting down Network Boot Integration")
        
        # Disconnect from message bus
        self.message_bus.unsubscribe("system.boot.hardware_init_complete", self._handle_hardware_init_complete)
        self.message_bus.unsubscribe("system.boot.complete", self._handle_boot_complete)
        self.message_bus.unsubscribe("system.network.internet_status_changed", self._handle_internet_status_changed)
        
        # Shut down network manager if it was initialized
        if self.network_manager:
            self.network_manager.shutdown()
            self.network_manager = None
