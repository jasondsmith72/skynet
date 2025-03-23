"""
Hardware Interface for ClarityOS

This module provides an abstraction layer for direct hardware access,
enabling the AI operating system to interact with physical devices.
"""

import asyncio
import json
import logging
import os
import platform
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set, Callable

from clarityos.core.message_bus import MessagePriority, system_bus

# Configure logging
logger = logging.getLogger(__name__)


class HardwareType(Enum):
    """Types of hardware components."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    DISPLAY = "display"
    NETWORK = "network"
    INPUT = "input"
    ACCELERATOR = "accelerator"
    AUDIO = "audio"
    PERIPHERAL = "peripheral"
    OTHER = "other"


class HardwareStatus(Enum):
    """Possible hardware status values."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class HardwareDevice:
    """Represents a hardware device in the system."""
    id: str
    type: HardwareType
    name: str
    description: str
    status: HardwareStatus = HardwareStatus.UNKNOWN
    properties: Dict[str, Any] = field(default_factory=dict)
    capabilities: Set[str] = field(default_factory=set)
    driver_loaded: bool = False
    last_updated: float = 0.0


class HardwareInterface:
    """
    Hardware interface for ClarityOS.
    
    This class provides an abstraction layer for interacting with hardware
    devices directly, allowing the AI OS to control and monitor physical
    hardware regardless of the underlying platform.
    """
    
    def __init__(self):
        """Initialize the hardware interface."""
        self.devices: Dict[str, HardwareDevice] = {}
        self.platform_info = self._detect_platform()
        self.event_handlers: Dict[str, List[Callable]] = {}
        self._initialized = False
        self._monitoring_task = None
    
    def _detect_platform(self) -> Dict[str, Any]:
        """Detect the current platform and architecture."""
        return {
            "system": platform.system(),
            "architecture": platform.machine(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor()
        }
    
    async def initialize(self) -> bool:
        """
        Initialize the hardware interface and detect devices.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        if self._initialized:
            logger.warning("Hardware interface already initialized")
            return True
        
        logger.info("Initializing hardware interface")
        
        try:
            # Detect platform-specific capabilities
            logger.info(f"Detected platform: {self.platform_info['system']} "
                         f"({self.platform_info['architecture']})")
            
            # Initialize device drivers based on platform
            if self.platform_info['system'] == 'Linux':
                await self._init_linux_devices()
            elif self.platform_info['system'] == 'Windows':
                await self._init_windows_devices()
            elif self.platform_info['system'] == 'Darwin':  # macOS
                await self._init_macos_devices()
            else:
                logger.warning(f"Unsupported platform: {self.platform_info['system']}")
                await self._init_generic_devices()
            
            # Set up periodic monitoring
            self._monitoring_task = asyncio.create_task(self._monitor_devices())
            
            # Subscribe to hardware-related messages
            await self._subscribe_to_messages()
            
            self._initialized = True
            logger.info(f"Hardware interface initialized with {len(self.devices)} devices")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing hardware interface: {str(e)}", exc_info=True)
            return False
    
    async def _init_linux_devices(self):
        """Initialize hardware devices on Linux platforms."""
        logger.info("Initializing Linux hardware devices")
        
        # On a real OS, this would use Linux-specific mechanisms like sysfs, udev, etc.
        # For now, we'll simulate device detection
        
        # Simulate CPU detection
        cpu_info = self._simulate_linux_cpu_info()
        cpu_id = "cpu-0"
        self.devices[cpu_id] = HardwareDevice(
            id=cpu_id,
            type=HardwareType.CPU,
            name=cpu_info.get("model_name", "Unknown CPU"),
            description=f"{cpu_info.get('cores', 1)} core processor",
            status=HardwareStatus.ONLINE,
            properties=cpu_info,
            capabilities={"execute", "interrupt"},
            driver_loaded=True
        )
        
        # Simulate memory detection
        memory_info = self._simulate_linux_memory_info()
        memory_id = "mem-0"
        self.devices[memory_id] = HardwareDevice(
            id=memory_id,
            type=HardwareType.MEMORY,
            name="System Memory",
            description=f"{memory_info.get('total_mb', 0)}MB RAM",
            status=HardwareStatus.ONLINE,
            properties=memory_info,
            capabilities={"read", "write", "allocate"},
            driver_loaded=True
        )
        
        # Simulate storage device detection
        disk_info = self._simulate_linux_disk_info()
        for idx, disk in enumerate(disk_info):
            disk_id = f"storage-{idx}"
            self.devices[disk_id] = HardwareDevice(
                id=disk_id,
                type=HardwareType.STORAGE,
                name=disk.get("name", f"Disk {idx}"),
                description=f"{disk.get('size_gb', 0)}GB {disk.get('type', 'Unknown')}",
                status=HardwareStatus.ONLINE,
                properties=disk,
                capabilities={"read", "write", "seek"},
                driver_loaded=True
            )
    
    async def _init_windows_devices(self):
        """Initialize hardware devices on Windows platforms."""
        logger.info("Initializing Windows hardware devices")
        
        # On a real OS, this would use Windows-specific mechanisms like WMI
        # For now, we'll simulate device detection similar to Linux
        
        # Simulate CPU detection
        cpu_info = self._simulate_windows_cpu_info()
        cpu_id = "cpu-0"
        self.devices[cpu_id] = HardwareDevice(
            id=cpu_id,
            type=HardwareType.CPU,
            name=cpu_info.get("name", "Unknown CPU"),
            description=f"{cpu_info.get('cores', 1)} core processor",
            status=HardwareStatus.ONLINE,
            properties=cpu_info,
            capabilities={"execute", "interrupt"},
            driver_loaded=True
        )
        
        # Simulate memory detection
        memory_info = self._simulate_windows_memory_info()
        memory_id = "mem-0"
        self.devices[memory_id] = HardwareDevice(
            id=memory_id,
            type=HardwareType.MEMORY,
            name="System Memory",
            description=f"{memory_info.get('total_mb', 0)}MB RAM",
            status=HardwareStatus.ONLINE,
            properties=memory_info,
            capabilities={"read", "write", "allocate"},
            driver_loaded=True
        )
        
        # Simulate storage device detection
        disk_info = self._simulate_windows_disk_info()
        for idx, disk in enumerate(disk_info):
            disk_id = f"storage-{idx}"
            self.devices[disk_id] = HardwareDevice(
                id=disk_id,
                type=HardwareType.STORAGE,
                name=disk.get("name", f"Disk {idx}"),
                description=f"{disk.get('size_gb', 0)}GB {disk.get('type', 'Unknown')}",
                status=HardwareStatus.ONLINE,
                properties=disk,
                capabilities={"read", "write", "seek"},
                driver_loaded=True
            )
    
    async def _init_macos_devices(self):
        """Initialize hardware devices on macOS platforms."""
        logger.info("Initializing macOS hardware devices")
        
        # On a real OS, this would use macOS-specific mechanisms like IOKit
        # For now, we'll use the generic device initialization
        await self._init_generic_devices()
    
    async def _init_generic_devices(self):
        """Initialize generic hardware devices for unsupported platforms."""
        logger.info("Initializing generic hardware devices")
        
        # Create a basic set of simulated devices
        cpu_id = "cpu-0"
        self.devices[cpu_id] = HardwareDevice(
            id=cpu_id,
            type=HardwareType.CPU,
            name="Generic CPU",
            description="Generic processor",
            status=HardwareStatus.ONLINE,
            properties={"cores": 4, "architecture": self.platform_info["architecture"]},
            capabilities={"execute"},
            driver_loaded=True
        )
        
        memory_id = "mem-0"
        self.devices[memory_id] = HardwareDevice(
            id=memory_id,
            type=HardwareType.MEMORY,
            name="Generic Memory",
            description="System RAM",
            status=HardwareStatus.ONLINE,
            properties={"total_mb": 4096, "type": "RAM"},
            capabilities={"read", "write"},
            driver_loaded=True
        )
        
        storage_id = "storage-0"
        self.devices[storage_id] = HardwareDevice(
            id=storage_id,
            type=HardwareType.STORAGE,
            name="Generic Storage",
            description="Primary storage device",
            status=HardwareStatus.ONLINE,
            properties={"size_gb": 256, "type": "SSD"},
            capabilities={"read", "write"},
            driver_loaded=True
        )
    
    def _simulate_linux_cpu_info(self) -> Dict[str, Any]:
        """Simulate Linux CPU information."""
        # In a real OS, this would read from /proc/cpuinfo
        return {
            "model_name": "Generic x86_64 Processor",
            "vendor_id": "GenuineIntel",
            "cores": 8,
            "threads": 16,
            "mhz": 3200.0,
            "cache_size_kb": 16384,
            "flags": ["fpu", "vme", "de", "pse", "tsc", "msr"]
        }
    
    def _simulate_linux_memory_info(self) -> Dict[str, Any]:
        """Simulate Linux memory information."""
        # In a real OS, this would read from /proc/meminfo
        return {
            "total_mb": 16384,
            "free_mb": 8192,
            "cached_mb": 4096,
            "swap_total_mb": 8192,
            "swap_free_mb": 8192
        }
    
    def _simulate_linux_disk_info(self) -> List[Dict[str, Any]]:
        """Simulate Linux disk information."""
        # In a real OS, this would use tools like lsblk or read from /proc/partitions
        return [
            {
                "name": "sda",
                "type": "SSD",
                "size_gb": 512,
                "model": "Generic SSD",
                "partitions": ["sda1", "sda2"],
                "filesystem": "ext4"
            },
            {
                "name": "sdb",
                "type": "HDD",
                "size_gb": 1024,
                "model": "Generic HDD",
                "partitions": ["sdb1"],
                "filesystem": "ext4"
            }
        ]
    
    def _simulate_windows_cpu_info(self) -> Dict[str, Any]:
        """Simulate Windows CPU information."""
        # In a real OS, this would use WMI queries
        return {
            "name": "Generic x86_64 Processor",
            "manufacturer": "Intel",
            "cores": 8,
            "threads": 16,
            "speed_mhz": 3200,
            "l2_cache_kb": 2048,
            "l3_cache_kb": 16384
        }
    
    def _simulate_windows_memory_info(self) -> Dict[str, Any]:
        """Simulate Windows memory information."""
        # In a real OS, this would use WMI queries
        return {
            "total_mb": 16384,
            "available_mb": 8192,
            "page_file_mb": 24576,
            "type": "DDR4"
        }
    
    def _simulate_windows_disk_info(self) -> List[Dict[str, Any]]:
        """Simulate Windows disk information."""
        # In a real OS, this would use WMI queries
        return [
            {
                "name": "C:",
                "type": "SSD",
                "size_gb": 512,
                "model": "Generic SSD",
                "filesystem": "NTFS",
                "free_space_gb": 256
            },
            {
                "name": "D:",
                "type": "HDD",
                "size_gb": 1024,
                "model": "Generic HDD",
                "filesystem": "NTFS",
                "free_space_gb": 512
            }
        ]
    
    async def _monitor_devices(self):
        """Periodically monitor hardware device status."""
        try:
            while True:
                # In a real OS, this would poll devices for status updates
                # For now, we'll simulate occasional status changes
                
                for device_id, device in self.devices.items():
                    # Simulate occasional status update (every 60 seconds on average)
                    if device.type == HardwareType.STORAGE and device_id.endswith("0"):
                        # Update storage properties to simulate changing free space
                        if "free_space_gb" in device.properties:
                            # Randomly adjust free space (simulating file operations)
                            current = device.properties["free_space_gb"]
                            device.properties["free_space_gb"] = max(0, current - 0.01)
                            device.last_updated = asyncio.get_event_loop().time()
                            
                            # Emit device update event
                            await self._emit_device_update(device_id, device)
                
                # Check again after 10 seconds
                await asyncio.sleep(10)
                
        except asyncio.CancelledError:
            logger.info("Hardware monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in hardware monitoring task: {str(e)}", exc_info=True)
    
    async def _subscribe_to_messages(self):
        """Subscribe to hardware-related messages on the system bus."""
        system_bus.subscribe(
            "hardware.query",
            self._handle_hardware_query,
            "hardware_interface"
        )
        
        system_bus.subscribe(
            "hardware.control",
            self._handle_hardware_control,
            "hardware_interface"
        )
    
    async def _handle_hardware_query(self, message):
        """Handle hardware query messages."""
        content = message.content
        query_type = content.get("type", "list")
        
        result = {}
        
        if query_type == "list":
            # List all devices
            result["devices"] = [
                {
                    "id": device.id,
                    "type": device.type.value,
                    "name": device.name,
                    "status": device.status.value
                }
                for device in self.devices.values()
            ]
        
        elif query_type == "details":
            # Get details for a specific device
            device_id = content.get("device_id")
            if device_id and device_id in self.devices:
                device = self.devices[device_id]
                result["device"] = {
                    "id": device.id,
                    "type": device.type.value,
                    "name": device.name,
                    "description": device.description,
                    "status": device.status.value,
                    "properties": device.properties,
                    "capabilities": list(device.capabilities),
                    "driver_loaded": device.driver_loaded
                }
            else:
                result["error"] = f"Device {device_id} not found"
        
        elif query_type == "platform":
            # Get platform information
            result["platform"] = self.platform_info
        
        else:
            result["error"] = f"Unknown query type: {query_type}"
        
        # Send response if reply_to is specified
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content=result,
                source="hardware_interface",
                reply_to=message.source
            )
    
    async def _handle_hardware_control(self, message):
        """Handle hardware control messages."""
        content = message.content
        device_id = content.get("device_id")
        action = content.get("action")
        parameters = content.get("parameters", {})
        
        result = {"success": False}
        
        if not device_id or device_id not in self.devices:
            result["error"] = f"Device {device_id} not found"
        elif not action:
            result["error"] = "No action specified"
        else:
            # Process the control action
            device = self.devices[device_id]
            result = await self._execute_device_action(device, action, parameters)
        
        # Send response if reply_to is specified
        if message.reply_to:
            await system_bus.publish(
                message_type=f"{message.message_type}.reply",
                content=result,
                source="hardware_interface",
                reply_to=message.source
            )
    
    async def _execute_device_action(self, device: HardwareDevice, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a control action on a device."""
        # In a real OS, this would use device-specific control mechanisms
        # For now, we'll implement some basic simulated actions
        
        if device.type == HardwareType.CPU:
            if action == "get_load":
                # Simulate CPU load information
                return {
                    "success": True,
                    "load": {
                        "total_percent": 25.5,
                        "per_core": [20.1, 30.2, 15.5, 36.2]
                    }
                }
            elif action == "set_governor":
                # Simulate setting CPU governor
                governor = parameters.get("governor", "performance")
                device.properties["governor"] = governor
                return {"success": True, "governor": governor}
        
        elif device.type == HardwareType.STORAGE:
            if action == "get_usage":
                # Simulate storage usage information
                return {
                    "success": True,
                    "usage": {
                        "total_gb": device.properties.get("size_gb", 0),
                        "free_gb": device.properties.get("free_space_gb", 0),
                        "used_percent": 50.0
                    }
                }
        
        # Default case for unsupported actions
        return {"success": False, "error": f"Unsupported action '{action}' for device type {device.type.value}"}
    
    async def _emit_device_update(self, device_id: str, device: HardwareDevice):
        """Emit a device update event on the message bus."""
        await system_bus.publish(
            message_type="hardware.device.updated",
            content={
                "device_id": device_id,
                "type": device.type.value,
                "name": device.name,
                "status": device.status.value,
                "properties": device.properties
            },
            source="hardware_interface",
            priority=MessagePriority.NORMAL
        )
    
    async def shutdown(self):
        """Shut down the hardware interface."""
        logger.info("Shutting down hardware interface")
        
        # Cancel monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        # In a real OS, this would perform proper hardware shutdown
        # For now, just mark all devices as offline
        for device in self.devices.values():
            device.status = HardwareStatus.OFFLINE
        
        self._initialized = False
        logger.info("Hardware interface shutdown complete")


# Singleton instance
hardware_interface = HardwareInterface()
