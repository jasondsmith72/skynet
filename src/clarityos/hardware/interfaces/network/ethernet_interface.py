"""
Ethernet Interface Implementation for ClarityOS

This module provides a concrete implementation of the NetworkInterface for
Ethernet hardware, supporting various Ethernet standards and configuration methods.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Union

from .base_interface import NetworkInterface, NetworkInterfaceType, NetworkStatus
from ...driver_framework import DriverManager
from ...safety.security_manager import SecurityManager

# Configure logging
logger = logging.getLogger(__name__)

class EthernetInterface(NetworkInterface):
    """Implementation for Ethernet network interfaces."""
    
    def __init__(self, name: str, driver_manager: DriverManager, security_manager: SecurityManager):
        super().__init__(name, NetworkInterfaceType.ETHERNET)
        self._driver_manager = driver_manager
        self._security_manager = security_manager
        self._link_speed = None
        self._duplex_mode = None
        self._auto_negotiation = True
        
    def initialize(self) -> bool:
        """Initialize the Ethernet interface hardware."""
        try:
            # Identify the appropriate driver for this interface
            self._driver = self._driver_manager.get_driver_for_device(self.name, "ethernet")
            
            if self._driver is None:
                logger.error(f"No suitable driver found for Ethernet interface {self.name}")
                return False
                
            # Initialize the driver
            driver_initialized = self._driver.initialize()
            
            if not driver_initialized:
                logger.error(f"Failed to initialize driver for Ethernet interface {self.name}")
                return False
                
            # Get the MAC address
            self.mac_address = self._driver.get_mac_address()
            
            # Apply security policies
            self._security_manager.apply_interface_policies(self)
            
            logger.info(f"Initialized Ethernet interface {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Ethernet interface {self.name}: {e}")
            return False
    
    def connect(self, timeout: int = 30) -> bool:
        """Connect to the network using DHCP."""
        try:
            self.status = NetworkStatus.CONNECTING
            self._connection_attempts += 1
            self._last_connection_time = time.time()
            
            # Request DHCP configuration
            dhcp_result = self._driver.request_dhcp(timeout)
            
            if not dhcp_result:
                logger.warning(f"DHCP request failed for interface {self.name}, falling back to static IP")
                # Fallback to static configuration if available
                # This would be implemented according to your static IP configuration strategy
                return False
                
            # Update network configuration from DHCP
            config = self._driver.get_network_config()
            self.ip_address = config.get('ip_address')
            self.subnet_mask = config.get('subnet_mask')
            self.gateway = config.get('gateway')
            self.dns_servers = config.get('dns_servers', [])
            
            # Test connectivity
            if not self.test_connectivity():
                logger.warning(f"Network connectivity test failed for {self.name}")
                self.status = NetworkStatus.LIMITED
                return False
                
            # Update status and metrics
            self.status = NetworkStatus.CONNECTED
            self._metrics['connection_time'] = time.time() - self._last_connection_time
            
            logger.info(f"Connected Ethernet interface {self.name} with IP {self.ip_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting Ethernet interface {self.name}: {e}")
            self.status = NetworkStatus.ERROR
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from the network."""
        try:
            self._driver.release_dhcp()
            self.status = NetworkStatus.DISCONNECTED
            self.ip_address = None
            self.subnet_mask = None
            self.gateway = None
            self.dns_servers = []
            
            logger.info(f"Disconnected Ethernet interface {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting Ethernet interface {self.name}: {e}")
            return False
    
    def get_signal_strength(self) -> Optional[int]:
        """Get link quality as a percentage."""
        try:
            link_info = self._driver.get_link_info()
            if link_info.get('link_up', False):
                # For Ethernet, we use link speed as a proxy for signal strength
                max_speed = link_info.get('max_speed', 1000)  # Default max of 1Gbps
                current_speed = link_info.get('current_speed', 0)
                
                if max_speed > 0:
                    return (current_speed / max_speed) * 100
            return 0
        except Exception as e:
            logger.error(f"Error getting signal strength for {self.name}: {e}")
            return None
    
    def scan_available_networks(self) -> List[Dict[str, Any]]:
        """For Ethernet, this mainly checks if the link is up."""
        try:
            link_info = self._driver.get_link_info()
            if link_info.get('link_up', False):
                return [{
                    'name': 'Wired Network',
                    'type': 'ethernet',
                    'quality': 100 if link_info.get('link_up') else 0,
                    'speed': link_info.get('current_speed', 0),
                    'duplex': link_info.get('duplex', 'unknown')
                }]
            return []
        except Exception as e:
            logger.error(f"Error scanning networks for {self.name}: {e}")
            return []
    
    def _update_metrics(self) -> None:
        """Update interface metrics."""
        try:
            stats = self._driver.get_interface_statistics()
            if stats:
                self._metrics.update(stats)
        except Exception as e:
            logger.error(f"Error updating metrics for {self.name}: {e}")
