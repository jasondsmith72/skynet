"""
WiFi Interface Implementation for ClarityOS

This module provides a concrete implementation of the NetworkInterface for
WiFi hardware, supporting various wireless standards and security protocols.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any, Union

from .base_interface import NetworkInterface, NetworkInterfaceType, NetworkStatus, NetworkSecurity
from ...driver_framework import DriverManager
from ...safety.security_manager import SecurityManager

# Configure logging
logger = logging.getLogger(__name__)

class WiFiInterface(NetworkInterface):
    """Implementation for WiFi network interfaces."""
    
    def __init__(self, name: str, driver_manager: DriverManager, security_manager: SecurityManager):
        super().__init__(name, NetworkInterfaceType.WIFI)
        self._driver_manager = driver_manager
        self._security_manager = security_manager
        self._current_network = None
        self._saved_networks = []
        self._security_type = None
        
    def initialize(self) -> bool:
        """Initialize the WiFi interface hardware."""
        try:
            # Similar to Ethernet, but for WiFi drivers
            self._driver = self._driver_manager.get_driver_for_device(self.name, "wifi")
            
            if self._driver is None:
                logger.error(f"No suitable driver found for WiFi interface {self.name}")
                return False
                
            # Initialize the driver
            driver_initialized = self._driver.initialize()
            
            if not driver_initialized:
                logger.error(f"Failed to initialize driver for WiFi interface {self.name}")
                return False
                
            # Get the MAC address
            self.mac_address = self._driver.get_mac_address()
            
            # Apply security policies
            self._security_manager.apply_interface_policies(self)
            
            # Load saved networks
            self._load_saved_networks()
            
            logger.info(f"Initialized WiFi interface {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing WiFi interface {self.name}: {e}")
            return False
    
    def connect(self, network_name: str = None, password: str = None, timeout: int = 30) -> bool:
        """Connect to a WiFi network."""
        try:
            self.status = NetworkStatus.CONNECTING
            self._connection_attempts += 1
            self._last_connection_time = time.time()
            
            # If no network specified, try to connect to saved networks
            if network_name is None:
                return self._connect_to_saved_network(timeout)
            
            # Connect to the specified network
            connection_result = self._driver.connect_to_network(
                network_name, 
                password,
                timeout
            )
            
            if not connection_result:
                logger.warning(f"Failed to connect to WiFi network {network_name}")
                self.status = NetworkStatus.ERROR
                return False
            
            # Update network configuration
            config = self._driver.get_network_config()
            self.ip_address = config.get('ip_address')
            self.subnet_mask = config.get('subnet_mask')
            self.gateway = config.get('gateway')
            self.dns_servers = config.get('dns_servers', [])
            self._current_network = network_name
            self._security_type = config.get('security_type')
            
            # Test connectivity
            if not self.test_connectivity():
                logger.warning(f"Network connectivity test failed for {self.name} on {network_name}")
                self.status = NetworkStatus.LIMITED
                return False
                
            # Update status and metrics
            self.status = NetworkStatus.CONNECTED
            self._metrics['connection_time'] = time.time() - self._last_connection_time
            
            # Save this network for future use
            self._save_network(network_name, password)
            
            logger.info(f"Connected WiFi interface {self.name} to {network_name} with IP {self.ip_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting WiFi interface {self.name}: {e}")
            self.status = NetworkStatus.ERROR
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from the WiFi network."""
        try:
            self._driver.disconnect()
            self.status = NetworkStatus.DISCONNECTED
            self.ip_address = None
            self.subnet_mask = None
            self.gateway = None
            self.dns_servers = []
            self._current_network = None
            
            logger.info(f"Disconnected WiFi interface {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting WiFi interface {self.name}: {e}")
            return False
    
    def get_signal_strength(self) -> Optional[int]:
        """Get signal strength as a percentage (0-100)."""
        try:
            signal_info = self._driver.get_signal_info()
            return signal_info.get('strength_percent', 0)
        except Exception as e:
            logger.error(f"Error getting signal strength for {self.name}: {e}")
            return None
    
    def scan_available_networks(self) -> List[Dict[str, Any]]:
        """Scan for available WiFi networks."""
        try:
            return self._driver.scan_networks()
        except Exception as e:
            logger.error(f"Error scanning networks for {self.name}: {e}")
            return []
    
    def _connect_to_saved_network(self, timeout: int) -> bool:
        """Try to connect to saved networks in order of preference."""
        if not self._saved_networks:
            logger.warning(f"No saved networks found for {self.name}")
            return False
            
        # Sort networks by preference (signal strength, security, etc.)
        available_networks = self.scan_available_networks()
        
        # Create a map of network names to details
        network_map = {network['name']: network for network in available_networks}
        
        # Try to connect to each saved network, in order of preference
        for saved_network in self._saved_networks:
            network_name = saved_network['name']
            
            # Check if this network is available
            if network_name in network_map:
                logger.info(f"Attempting to connect to saved network: {network_name}")
                
                # Try to connect
                if self.connect(network_name, saved_network.get('password'), timeout):
                    return True
        
        logger.warning(f"Failed to connect to any saved networks for {self.name}")
        return False
    
    def _load_saved_networks(self) -> None:
        """Load saved WiFi networks from secure storage."""
        try:
            # This is a placeholder - would actually load from secure storage
            # self._saved_networks = secure_storage.load('wifi_networks')
            
            # For now, just initialize as empty list
            self._saved_networks = []
        except Exception as e:
            logger.error(f"Error loading saved networks for {self.name}: {e}")
            self._saved_networks = []
    
    def _save_network(self, network_name: str, password: str = None) -> None:
        """Save a WiFi network for future use."""
        try:
            # Check if this network is already saved
            for network in self._saved_networks:
                if network['name'] == network_name:
                    # Update existing entry
                    if password:
                        network['password'] = password
                    return
            
            # Add new entry
            self._saved_networks.append({
                'name': network_name,
                'password': password,
                'last_connected': time.time()
            })
            
            # Save to secure storage
            # secure_storage.save('wifi_networks', self._saved_networks)
        except Exception as e:
            logger.error(f"Error saving network {network_name}: {e}")
    
    def _update_metrics(self) -> None:
        """Update interface metrics."""
        try:
            stats = self._driver.get_interface_statistics()
            if stats:
                self._metrics.update(stats)
                
            # Add WiFi-specific metrics
            signal_info = self._driver.get_signal_info()
            if signal_info:
                self._metrics.update({
                    'signal_strength': signal_info.get('strength_percent', 0),
                    'noise_level': signal_info.get('noise_level', 0),
                    'frequency': signal_info.get('frequency', 0),
                    'channel': signal_info.get('channel', 0)
                })
        except Exception as e:
            logger.error(f"Error updating metrics for {self.name}: {e}")
