"""
Network Manager for ClarityOS (Part 2)

This module contains additional methods for the NetworkManager class.
"""

import logging
from typing import Dict, Any, Optional

from .base_interface import NetworkInterfaceType

# Configure logging
logger = logging.getLogger(__name__)

class NetworkManagerPart2:
    """Additional methods for the NetworkManager class."""
    
    def _handle_connect_request(self, message: Dict[str, Any]) -> None:
        """Handle network connection requests."""
        try:
            interface_name = message.get('interface')
            network_name = message.get('network')
            password = message.get('password')
            timeout = message.get('timeout', 30)
            
            # If no specific interface requested, choose the best available
            if interface_name is None:
                from .network_manager_operations import NetworkManagerOperations
                interface_name = NetworkManagerOperations.choose_best_interface(self.interfaces)
                
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
                from .network_manager_operations import NetworkManagerOperations
                new_primary = NetworkManagerOperations.choose_connected_interface(self.interfaces)
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
    
    def _set_primary_interface(self, interface_name: str) -> None:
        """Set the primary network interface."""
        if interface_name in self.interfaces:
            # Reset old primary
            if self.primary_interface and self.primary_interface in self.interfaces:
                self.interfaces[self.primary_interface].set_as_primary(False)
            
            # Set new primary
            self.primary_interface = interface_name
            self.interfaces[interface_name].set_as_primary(True)
            
            logger.info(f"Set {interface_name} as primary network interface")
            
            # Notify system
            self.message_bus.publish("system.network.primary_interface_changed", {
                "interface": interface_name
            })
    
    def _start_connection_monitoring(self) -> None:
        """Start monitoring network connections."""
        try:
            if self._connection_monitor_thread is None:
                self._stop_monitoring_event.clear()
                
                from .network_manager_operations import NetworkManagerOperations
                
                # Define callbacks
                def set_primary_callback(interface_name: str):
                    self._set_primary_interface(interface_name)
                    
                def internet_status_callback(connected: bool):
                    self._internet_connected = connected
                    self.message_bus.publish("system.network.internet_status_changed", {
                        "connected": connected
                    })
                
                # Start monitoring thread
                self._connection_monitor_thread = threading.Thread(
                    target=NetworkManagerOperations.monitor_connections,
                    args=(
                        self.interfaces,
                        self.primary_interface,
                        set_primary_callback,
                        internet_status_callback,
                        self._stop_monitoring_event
                    ),
                    daemon=True
                )
                
                self._connection_monitor_thread.start()
                logger.info("Started network connection monitoring")
        except Exception as e:
            logger.error(f"Error starting connection monitoring: {e}")
    
    def _stop_connection_monitoring(self) -> None:
        """Stop monitoring network connections."""
        if self._connection_monitor_thread is not None:
            self._stop_monitoring_event.set()
            self._connection_monitor_thread.join(timeout=1.0)
            self._connection_monitor_thread = None
            logger.info("Stopped network connection monitoring")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of all network interfaces."""
        from .network_manager_operations import NetworkManagerOperations
        return NetworkManagerOperations.get_network_status(
            self.interfaces,
            self._internet_connected,
            self.primary_interface
        )
    
    def connect_best_interface(self, timeout: int = 30) -> bool:
        """Connect to the best available network interface."""
        try:
            # Use operation class to choose and connect
            from .network_manager_operations import NetworkManagerOperations
            return NetworkManagerOperations.connect_best_interface(
                self.interfaces,
                self._set_primary_interface,
                timeout
            )
        except Exception as e:
            logger.error(f"Error connecting best interface: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shut down the Network Manager."""
        logger.info("Shutting down Network Manager")
        
        # Stop connection monitoring
        self._stop_connection_monitoring()
        
        # Disconnect all interfaces
        for name, interface in self.interfaces.items():
            if interface.is_connected():
                interface.disconnect()
        
        # Unsubscribe from messages
        self.message_bus.unsubscribe("system.hardware.discovered", self._handle_hardware_discovered)
        self.message_bus.unsubscribe("system.network.connect_request", self._handle_connect_request)
        self.message_bus.unsubscribe("system.network.disconnect_request", self._handle_disconnect_request)
