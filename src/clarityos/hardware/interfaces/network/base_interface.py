"""
Base Network Interface for ClarityOS

This module defines the base interface for all network hardware abstractions,
providing a common API for different types of network hardware.
"""

import time
import socket
import logging
import urllib.request
from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any, Union

# Configure logging
logger = logging.getLogger(__name__)

class NetworkInterfaceType(Enum):
    """Enum defining the types of network interfaces supported."""
    ETHERNET = "ethernet"
    WIFI = "wifi"
    CELLULAR = "cellular"
    BLUETOOTH = "bluetooth"
    VIRTUAL = "virtual"
    UNKNOWN = "unknown"

class NetworkStatus(Enum):
    """Enum defining possible network connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    LIMITED = "limited"

class NetworkSecurity(Enum):
    """Enum defining network security levels."""
    OPEN = "open"
    WEP = "wep"  # Insecure, but included for legacy detection
    WPA = "wpa"
    WPA2 = "wpa2"
    WPA3 = "wpa3"
    ENTERPRISE = "enterprise"
    VPN = "vpn"

class NetworkInterface(ABC):
    """Abstract base class for all network interfaces."""
    
    def __init__(self, name: str, interface_type: NetworkInterfaceType):
        self.name = name
        self.type = interface_type
        self.status = NetworkStatus.DISCONNECTED
        self.mac_address = None
        self.ip_address = None
        self.subnet_mask = None
        self.gateway = None
        self.dns_servers = []
        self._is_primary = False
        self._driver = None
        self._security_manager = None
        self._connection_attempts = 0
        self._last_connection_time = 0
        self._metrics = {
            "bytes_sent": 0,
            "bytes_received": 0,
            "packets_sent": 0,
            "packets_received": 0,
            "errors": 0,
            "connection_time": 0
        }
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the network interface hardware."""
        pass
    
    @abstractmethod
    def connect(self, timeout: int = 30) -> bool:
        """Connect to the network."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the network."""
        pass
    
    @abstractmethod
    def get_signal_strength(self) -> Optional[int]:
        """Get signal strength as a percentage (0-100)."""
        pass
    
    @abstractmethod
    def scan_available_networks(self) -> List[Dict[str, Any]]:
        """Scan for available networks (primarily for wireless)."""
        pass
    
    def is_connected(self) -> bool:
        """Check if the interface is connected."""
        return self.status == NetworkStatus.CONNECTED
    
    def set_as_primary(self, is_primary: bool = True) -> None:
        """Set this interface as the primary network interface."""
        self._is_primary = is_primary
    
    def is_primary(self) -> bool:
        """Check if this is the primary network interface."""
        return self._is_primary
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this interface."""
        self._update_metrics()
        return self._metrics
    
    def _update_metrics(self) -> None:
        """Update interface metrics."""
        # Subclasses should implement to update real-time metrics
        pass
    
    def test_connectivity(self, target: str = "8.8.8.8", port: int = 53, timeout: int = 5) -> bool:
        """Test basic network connectivity by attempting to connect to a target."""
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((target, port))
            return True
        except Exception as e:
            logger.warning(f"Connectivity test failed: {e}")
            return False
    
    def test_internet(self, url: str = "http://www.google.com", timeout: int = 5) -> bool:
        """Test internet connectivity by attempting to access a known website."""
        try:
            urllib.request.urlopen(url, timeout=timeout)
            return True
        except Exception as e:
            logger.warning(f"Internet test failed: {e}")
            return False
