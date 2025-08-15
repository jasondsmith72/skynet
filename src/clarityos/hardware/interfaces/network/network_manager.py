"""
Network Manager for ClarityOS

Manages network interfaces and provides a unified API for network operations.
Responsible for interface discovery, configuration, and connection management.
"""

import os
import time
import json
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any, Union

from .base_interface import NetworkInterface, NetworkInterfaceType, NetworkStatus
from .ethernet_interface import EthernetInterface
from .wifi_interface import WiFiInterface
from .network_manager_operations import NetworkManagerOperations
from .safe_driver_manager import SafeNetworkDriverManager
from ...driver_framework import DriverManager
from ...safety.security_manager import SecurityManager
from ...knowledge_repository import HardwareKnowledgeRepository as KnowledgeRepository
from ...hal import HardwareAbstractionLayer
from clarityos.core.message_bus import MessageBus

# Configure logging
logger = logging.getLogger(__name__)

class NetworkManager:
    """
    Manages network interfaces and provides a unified API for network operations.
    Responsible for interface discovery, configuration, and connection management.
    """
    
    def __init__(self, message_bus: MessageBus, driver_manager: DriverManager, 
                 security_manager: SecurityManager, knowledge_repository: KnowledgeRepository,
                 hal: Optional[HardwareAbstractionLayer] = None):
        self.message_bus = message_bus
        self.driver_manager = driver_manager
        self.security_manager = security_manager
        self.knowledge_repository = knowledge_repository
        self.hal = hal
        self.safe_driver_manager = None
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.primary_interface = None
        self._internet_connected = False
        self._discovery_complete = False
        self._connection_monitor_thread = None
        self._stop_monitoring_event = threading.Event()
        
    def initialize(self) -> bool:
        """Initialize the Network Manager."""
        try:
            logger.info("Initializing Network Manager")
            
            # Initialize safe driver manager if HAL is available
            if self.hal:
                self.safe_driver_manager = SafeNetworkDriverManager(
                    self.driver_manager,
                    self.hal,
                    self.security_manager,
                    self.knowledge_repository
                )
                self.safe_driver_manager.initialize()
            
            # Subscribe to relevant messages
            self.message_bus.subscribe("system.hardware.discovered", self._handle_hardware_discovered)
            self.message_bus.subscribe("system.network.connect_request", self._handle_connect_request)
            self.message_bus.subscribe("system.network.disconnect_request", self._handle_disconnect_request)
            
            # Start interface discovery
            self._discover_interfaces()
            
            # Start connection monitoring
            self._start_connection_monitoring()
            
            logger.info("Network Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Network Manager: {e}")
            return False
    
    def _discover_interfaces(self) -> None:
        """Discover network interfaces."""
        try:
            logger.info("Starting network interface discovery")
            
            # Discover Ethernet interfaces
            ethernet_devices = self.driver_manager.discover_devices("ethernet")
            for device in ethernet_devices:
                interface = EthernetInterface(
                    device['name'], 
                    self.driver_manager,
                    self.security_manager
                )
                if interface.initialize():
                    self.interfaces[device['name']] = interface
                    logger.info(f"Discovered Ethernet interface: {device['name']}")
            
            # Discover WiFi interfaces
            wifi_devices = self.driver_manager.discover_devices("wifi")
            for device in wifi_devices:
                interface = WiFiInterface(
                    device['name'], 
                    self.driver_manager,
                    self.security_manager
                )
                if interface.initialize():
                    self.interfaces[device['name']] = interface
                    logger.info(f"Discovered WiFi interface: {device['name']}")
            
            # Mark discovery as complete
            self._discovery_complete = True
            
            # Notify system about discovered interfaces
            self.message_bus.publish("system.network.interfaces_discovered", {
                "interfaces": list(self.interfaces.keys())
            })
            
            # If no interfaces found, log a warning
            if not self.interfaces:
                logger.warning("No network interfaces discovered")
            else:
                logger.info(f"Discovered {len(self.interfaces)} network interfaces")
                
        except Exception as e:
            logger.error(f"Error discovering network interfaces: {e}")
            
    def _handle_hardware_discovered(self, message: Dict[str, Any]) -> None:
        """Handle hardware discovery events."""
        try:
            device = message.get('device', {})
            if device.get('type') in ['ethernet', 'wifi']:
                logger.info(f"New network device discovered: {device.get('name')}")
                
                # Check if this is a new device
                if device.get('name') not in self.interfaces:
                    # Create and initialize the appropriate interface
                    if device.get('type') == 'ethernet':
                        interface = EthernetInterface(
                            device.get('name'), 
                            self.driver_manager,
                            self.security_manager
                        )
                    else:  # wifi
                        interface = WiFiInterface(
                            device.get('name'), 
                            self.driver_manager,
                            self.security_manager
                        )
                    
                    if interface.initialize():
                        self.interfaces[device.get('name')] = interface
                        logger.info(f"Added new network interface: {device.get('name')}")
                        
                        # Notify system about new interface
                        self.message_bus.publish("system.network.interface_added", {
                            "interface": device.get('name'),
                            "type": device.get('type')
                        })
        except Exception as e:
            logger.error(f"Error handling hardware discovery event: {e}")
