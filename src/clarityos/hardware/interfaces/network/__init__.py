"""
Network Interface Package for ClarityOS

This package provides network interfaces and connectivity management 
for ClarityOS with a focus on secure, bootable operations.
"""

from .network_manager import NetworkManager
from .base_interface import NetworkInterface, NetworkInterfaceType, NetworkStatus, NetworkSecurity
from .ethernet_interface import EthernetInterface
from .wifi_interface import WiFiInterface

__all__ = [
    'NetworkManager',
    'NetworkInterface',
    'NetworkInterfaceType',
    'NetworkStatus',
    'NetworkSecurity',
    'EthernetInterface',
    'WiFiInterface'
]
