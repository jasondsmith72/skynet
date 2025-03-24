"""
Hardware Interface Protocols for ClarityOS

This module defines standard interface protocols for different types of hardware,
providing a consistent interface regardless of the underlying hardware implementation.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set, Callable, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

class DeviceClass(Enum):
    """Classes of hardware devices."""
    STORAGE = auto()      # Storage devices (disks, SSDs, etc.)
    NETWORK = auto()      # Network interfaces
    DISPLAY = auto()      # Display devices
    INPUT = auto()        # Input devices (keyboard, mouse, etc.)
    PROCESSOR = auto()    # CPU and coprocessors
    MEMORY = auto()       # Memory devices
    AUDIO = auto()        # Audio devices
    POWER = auto()        # Power management devices
    THERMAL = auto()      # Thermal sensors and cooling
    SECURITY = auto()     # Security devices (TPM, etc.)
    ACCELERATOR = auto()  # Hardware accelerators (GPU, AI, etc.)
    OTHER = auto()        # Other devices

class PowerState(Enum):
    """Power states for devices."""
    FULL_POWER = auto()   # Device is fully powered
    LOW_POWER = auto()    # Device is in low power mode
    STANDBY = auto()      # Device is in standby mode
    OFF = auto()          # Device is powered off

@runtime_checkable
class HardwareDeviceProtocol(Protocol):
    """Protocol for hardware devices."""
    
    @property
    def id(self) -> str:
        """Get the device identifier."""
        ...
        
    @property
    def name(self) -> str:
        """Get the device name."""
        ...
        
    @property
    def device_class(self) -> DeviceClass:
        """Get the device class."""
        ...
        
    async def initialize(self) -> bool:
        """Initialize the device."""
        ...
        
    async def shutdown(self) -> bool:
        """Shut down the device."""
        ...
        
    async def reset(self) -> bool:
        """Reset the device."""
        ...
        
    async def get_status(self) -> Dict[str, Any]:
        """Get the device status."""
        ...
        
    async def set_power_state(self, state: PowerState) -> bool:
        """Set the device power state."""
        ...
        
    async def get_power_state(self) -> PowerState:
        """Get the device power state."""
        ...

@runtime_checkable
class StorageDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for storage devices."""
    
    async def read(self, offset: int, size: int) -> bytes:
        """Read data from the storage device."""
        ...
        
    async def write(self, offset: int, data: bytes) -> bool:
        """Write data to the storage device."""
        ...
        
    async def get_size(self) -> int:
        """Get the size of the storage device."""
        ...
        
    async def flush(self) -> bool:
        """Flush any cached data to the storage device."""
        ...

@runtime_checkable
class NetworkDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for network devices."""
    
    async def send_packet(self, packet: bytes) -> bool:
        """Send a packet over the network."""
        ...
        
    async def receive_packet(self) -> bytes:
        """Receive a packet from the network."""
        ...
        
    async def get_mac_address(self) -> str:
        """Get the MAC address of the network device."""
        ...
        
    async def set_promiscuous_mode(self, enabled: bool) -> bool:
        """Enable or disable promiscuous mode."""
        ...

@runtime_checkable
class DisplayDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for display devices."""
    
    async def set_mode(self, width: int, height: int, bpp: int) -> bool:
        """Set the display mode."""
        ...
        
    async def get_modes(self) -> List[Dict[str, int]]:
        """Get supported display modes."""
        ...
        
    async def update_framebuffer(self, buffer: bytes) -> bool:
        """Update the display framebuffer."""
        ...
        
    async def get_edid(self) -> bytes:
        """Get EDID information."""
        ...

@runtime_checkable
class InputDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for input devices."""
    
    async def read_input(self) -> Dict[str, Any]:
        """Read input from the device."""
        ...
        
    async def set_callback(self, callback: Callable) -> bool:
        """Set a callback for input events."""
        ...
        
    async def get_capabilities(self) -> Set[str]:
        """Get device capabilities."""
        ...

@runtime_checkable
class ProcessorDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for processor devices."""
    
    async def get_core_count(self) -> int:
        """Get the number of processor cores."""
        ...
        
    async def get_frequency(self) -> int:
        """Get the processor frequency in Hz."""
        ...
        
    async def set_frequency(self, frequency: int) -> bool:
        """Set the processor frequency in Hz."""
        ...
        
    async def get_temperature(self) -> float:
        """Get the processor temperature in degrees Celsius."""
        ...

@runtime_checkable
class MemoryDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for memory devices."""
    
    async def get_size(self) -> int:
        """Get the memory size in bytes."""
        ...
        
    async def get_type(self) -> str:
        """Get the memory type."""
        ...
        
    async def get_speed(self) -> int:
        """Get the memory speed."""
        ...
        
    async def test(self) -> bool:
        """Test the memory."""
        ...

@runtime_checkable
class AudioDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for audio devices."""
    
    async def play(self, buffer: bytes, sample_rate: int, channels: int) -> bool:
        """Play audio."""
        ...
        
    async def record(self, sample_rate: int, channels: int, duration: float) -> bytes:
        """Record audio."""
        ...
        
    async def set_volume(self, volume: float) -> bool:
        """Set the audio volume."""
        ...
        
    async def get_volume(self) -> float:
        """Get the audio volume."""
        ...

@runtime_checkable
class PowerDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for power management devices."""
    
    async def get_battery_level(self) -> float:
        """Get the battery level as a percentage."""
        ...
        
    async def get_power_source(self) -> str:
        """Get the current power source."""
        ...
        
    async def set_system_power_state(self, state: PowerState) -> bool:
        """Set the system power state."""
        ...
        
    async def get_system_power_state(self) -> PowerState:
        """Get the system power state."""
        ...

@runtime_checkable
class ThermalDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for thermal devices."""
    
    async def get_temperature(self) -> float:
        """Get the temperature in degrees Celsius."""
        ...
        
    async def get_fan_speed(self) -> int:
        """Get the fan speed in RPM."""
        ...
        
    async def set_fan_speed(self, speed: int) -> bool:
        """Set the fan speed in RPM."""
        ...
        
    async def get_thermal_zones(self) -> List[Dict[str, Any]]:
        """Get information about thermal zones."""
        ...

@runtime_checkable
class SecurityDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for security devices."""
    
    async def get_capabilities(self) -> Set[str]:
        """Get security capabilities."""
        ...
        
    async def secure_boot_enabled(self) -> bool:
        """Check if secure boot is enabled."""
        ...
        
    async def tpm_present(self) -> bool:
        """Check if a TPM is present."""
        ...
        
    async def encrypt_data(self, data: bytes, key_id: str) -> bytes:
        """Encrypt data using the security device."""
        ...
        
    async def decrypt_data(self, data: bytes, key_id: str) -> bytes:
        """Decrypt data using the security device."""
        ...

@runtime_checkable
class AcceleratorDeviceProtocol(HardwareDeviceProtocol, Protocol):
    """Protocol for hardware accelerators."""
    
    async def get_capabilities(self) -> Set[str]:
        """Get accelerator capabilities."""
        ...
        
    async def execute(self, operation: str, data: bytes) -> bytes:
        """Execute an operation on the accelerator."""
        ...
        
    async def get_memory(self) -> int:
        """Get the amount of accelerator memory in bytes."""
        ...
        
    async def get_performance(self) -> Dict[str, Any]:
        """Get performance metrics."""
        ...

# Map device classes to their corresponding protocols
PROTOCOL_MAP = {
    DeviceClass.STORAGE: StorageDeviceProtocol,
    DeviceClass.NETWORK: NetworkDeviceProtocol,
    DeviceClass.DISPLAY: DisplayDeviceProtocol,
    DeviceClass.INPUT: InputDeviceProtocol,
    DeviceClass.PROCESSOR: ProcessorDeviceProtocol,
    DeviceClass.MEMORY: MemoryDeviceProtocol,
    DeviceClass.AUDIO: AudioDeviceProtocol,
    DeviceClass.POWER: PowerDeviceProtocol,
    DeviceClass.THERMAL: ThermalDeviceProtocol,
    DeviceClass.SECURITY: SecurityDeviceProtocol,
    DeviceClass.ACCELERATOR: AcceleratorDeviceProtocol,
    DeviceClass.OTHER: HardwareDeviceProtocol
}

def get_protocol_for_device_class(device_class: DeviceClass) -> type:
    """
    Get the appropriate protocol for a device class.
    
    Args:
        device_class: The device class
        
    Returns:
        The protocol class for the device class
    """
    return PROTOCOL_MAP.get(device_class, HardwareDeviceProtocol)
