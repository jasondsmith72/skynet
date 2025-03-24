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
from ....driver_framework import DriverManager
from ....safety.security_manager import SecurityManager
from ....knowledge_repository import KnowledgeRepository
from ....core.message_bus import MessageBus

# Configure logging
logger = logging.getLogger(__name__)

class NetworkManager:
    """
    Manages network interfaces and provides a unified API for network operations.
    Responsible for interface discovery, configuration, and connection management.
    """
    
    def __init__(self, message_bus: MessageBus, driver_manager: DriverManager, 
                 security_manager: SecurityManager, knowledge_repository: KnowledgeRepository):
        self.message_bus = message_bus
        self.driver_manager = driver_manager
        self.security_manager = security_manager
        self.knowledge_repository = knowledge_repository
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.primary_interface = None
        self._internet_connected = False
        self._discovery_complete = False
        self._connection_monitor_thread = None
        self._stop_monitoring = False
        
    def initialize(self) -> bool:
        """Initialize the Network Manager."""
        try:
            logger.info("Initializing Network Manager")
            
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
    
    def _handle_connect_request(self, message: Dict[str, Any]) -> None:
        """Handle network connection requests."""
        try:
            interface_name = message.get('interface')
            network_name = message.get('network')
            password = message.get('password')
            timeout = message.get('timeout', 30)
            
            # If no specific interface requested, choose the best available
            if interface_name is None:
                interface_name = self._choose_best_interface()
                
            if interface_name is None or interface_name not in self.interfaces:
                logger.error(f"Invalid interface requested: {interface_name}")
                self.message_bus.publish("system.network.connect_response", {
                    "success": False,
                    "error": f"Invalid interface: {interface_name}"
                })
                return
                
            interface = self.interfaces[interface_name]
            
            # Connect based on interface type
            success = False
            if interface.type == NetworkInterfaceType.ETHERNET:
                success = interface.connect(timeout)
            elif interface.type == NetworkInterfaceType.WIFI:
                success = interface.connect(network_name, password, timeout)
                
            # Update primary interface if needed
            if success and (self.primary_interface is None or message.get('set_primary', False)):
                self._set_primary_interface(interface_name)
            
            # Publish response
            self.message_bus.publish("system.network.connect_response", {
                "success": success,
                "interface": interface_name,
                "status": interface.status.value,
                "ip_address": interface.ip_address
            })
            
        except Exception as e:
            logger.error(f"Error handling connect request: {e}")
            self.message_bus.publish("system.network.connect_response", {
                "success": False,
                "error": str(e)
            })
    
    def _handle_disconnect_request(self, message: Dict[str, Any]) -> None:
        """Handle network disconnection requests."""
        try:
            interface_name = message.get('interface')
            
            if interface_name not in self.interfaces:
                logger.error(f"Invalid interface requested for disconnect: {interface_name}")
                self.message_bus.publish("system.network.disconnect_response", {
                    "success": False,
                    "error": f"Invalid interface: {interface_name}"
                })
                return
                
            interface = self.interfaces[interface_name]
            success = interface.disconnect()
            
            # Update primary interface if needed
            if success and self.primary_interface == interface_name:
                self.primary_interface = None
                # Try to find a new primary interface
                new_primary = self._choose_connected_interface()
                if new_primary:
                    self._set_primary_interface(new_primary)
            
            # Publish response
            self.message_bus.publish("system.network.disconnect_response", {
                "success": success,
                "interface": interface_name
            })
            
        except Exception as e:
            logger.error(f"Error handling disconnect request: {e}")
            self.message_bus.publish("system.network.disconnect_response", {
                "success": False,
                "error": str(e)
            })
