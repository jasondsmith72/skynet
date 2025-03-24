"""
Network Manager Operations for ClarityOS

Additional operations for the NetworkManager class.
This module contains helper functions and monitor operations
to maintain network connectivity during the boot process.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any, Union

from .base_interface import NetworkInterface, NetworkInterfaceType, NetworkStatus

# Configure logging
logger = logging.getLogger(__name__)

class NetworkManagerOperations:
    """
    Provides operation methods for the NetworkManager class.
    These methods are separated to keep the main class size manageable.
    """
    
    @staticmethod
    def choose_best_interface(interfaces: Dict[str, NetworkInterface]) -> Optional[str]:
        """Choose the best interface for connection based on type and availability."""
        # Prefer Ethernet over WiFi
        for name, interface in interfaces.items():
            if interface.type == NetworkInterfaceType.ETHERNET:
                link_info = interface.scan_available_networks()
                if link_info and link_info[0].get('quality', 0) > 0:
                    return name
        
        # If no suitable Ethernet, try WiFi
        best_wifi = None
        best_signal = -1
        
        for name, interface in interfaces.items():
            if interface.type == NetworkInterfaceType.WIFI:
                networks = interface.scan_available_networks()
                for network in networks:
                    if network.get('quality', 0) > best_signal:
                        best_wifi = name
                        best_signal = network.get('quality', 0)
        
        return best_wifi
    
    @staticmethod
    def choose_connected_interface(interfaces: Dict[str, NetworkInterface]) -> Optional[str]:
        """Choose a connected interface to be the new primary."""
        for name, interface in interfaces.items():
            if interface.is_connected():
                return name
        return None
    
    @staticmethod
    def monitor_connections(interfaces: Dict[str, NetworkInterface],
                            primary_interface: Optional[str], 
                            set_primary_callback,
                            internet_status_callback,
                            stop_event: threading.Event) -> None:
        """Monitor active network connections and internet connectivity."""
        check_interval = 10  # seconds
        internet_check_interval = 30  # seconds
        last_internet_check = 0
        internet_connected = False
        
        while not stop_event.is_set():
            try:
                # Check each interface
                for name, interface in interfaces.items():
                    if interface.is_connected():
                        # Update interface metrics
                        interface._update_metrics()
                
                # Check internet connectivity periodically
                current_time = time.time()
                if current_time - last_internet_check > internet_check_interval:
                    new_internet_status = False
                    
                    # Try primary interface first
                    if primary_interface and primary_interface in interfaces:
                        new_internet_status = interfaces[primary_interface].test_internet()
                    
                    # If primary is not connected, try any connected interface
                    if not new_internet_status:
                        for name, interface in interfaces.items():
                            if interface.is_connected() and interface.test_internet():
                                new_internet_status = True
                                # Make this the primary if we don't have one
                                if primary_interface is None:
                                    set_primary_callback(name)
                                break
                    
                    # Notify if internet status changed
                    if new_internet_status != internet_connected:
                        internet_connected = new_internet_status
                        internet_status_callback(internet_connected)
                    
                    last_internet_check = current_time
                
                # Sleep for a bit
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring connections: {e}")
                time.sleep(check_interval)

    @staticmethod
    def get_network_status(interfaces: Dict[str, NetworkInterface], 
                          internet_connected: bool,
                          primary_interface: Optional[str]) -> Dict[str, Any]:
        """Get the current status of all network interfaces."""
        status = {
            "interfaces": {},
            "internet_connected": internet_connected,
            "primary_interface": primary_interface
        }
        
        for name, interface in interfaces.items():
            status["interfaces"][name] = {
                "type": interface.type.value,
                "status": interface.status.value,
                "connected": interface.is_connected(),
                "ip_address": interface.ip_address,
                "mac_address": interface.mac_address,
                "is_primary": interface.is_primary(),
                "signal_strength": interface.get_signal_strength(),
                "metrics": interface.get_metrics()
            }
        
        return status
    
    @staticmethod
    def connect_best_interface(interfaces: Dict[str, NetworkInterface],
                              set_primary_callback, timeout: int = 30) -> bool:
        """Connect to the best available network interface."""
        interface_name = NetworkManagerOperations.choose_best_interface(interfaces)
        
        if interface_name is None:
            logger.error("No suitable interface found for connection")
            return False
            
        interface = interfaces[interface_name]
        
        # Connect based on interface type
        success = False
        if interface.type == NetworkInterfaceType.ETHERNET:
            success = interface.connect(timeout)
        elif interface.type == NetworkInterfaceType.WIFI:
            # For WiFi, scan and try known networks
            networks = interface.scan_available_networks()
            if networks:
                # This would use saved networks in WiFiInterface implementation
                success = interface.connect(timeout=timeout)
                
        # Set as primary if successful
        if success:
            set_primary_callback(interface_name)
            
        return success
