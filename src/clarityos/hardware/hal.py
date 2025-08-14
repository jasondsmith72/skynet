"""
Hardware Abstraction Layer (HAL) for ClarityOS

This module provides a uniform interface for interacting with hardware
components, abstracting the low-level details of different hardware types
and allowing ClarityOS to operate across diverse hardware platforms.
"""

import logging
import time
import platform
import os
import subprocess
import json
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any, Callable

from src.clarityos.hardware.firmware_interface import FirmwareInterface

logger = logging.getLogger(__name__)

class DeviceClass(Enum):
    """Classification of hardware devices."""
    UNKNOWN = auto()
    PROCESSOR = auto()
    MEMORY = auto()
    STORAGE = auto()
    DISPLAY = auto()
    NETWORK = auto()
    INPUT = auto()
    AUDIO = auto()
    BATTERY = auto()
    BUS = auto()
    BRIDGE = auto()
    COMMUNICATION = auto()
    SECURITY = auto()
    ACCELERATOR = auto()

class DeviceState(Enum):
    """Possible states of a hardware device."""
    UNKNOWN = auto()
    NOT_PRESENT = auto()
    DISABLED = auto()
    ENABLED = auto()
    SUSPENDED = auto()
    ERROR = auto()

class Device:
    """Represents a hardware device in the system."""
    
    def __init__(self, 
                 device_id: str,
                 device_class: DeviceClass,
                 name: str,
                 vendor: str = "Unknown",
                 model: str = "Unknown"):
        self.device_id = device_id
        self.device_class = device_class
        self.name = name
        self.vendor = vendor
        self.model = model
        self.state = DeviceState.UNKNOWN
        self.driver = None
        self.resources = {}
        self.properties = {}
        self.capabilities = {}
        self.parent = None
        self.children = []
    
    def __str__(self) -> str:
        return f"{self.name} ({self.device_class.name}, ID: {self.device_id})"

class DeviceManager:
    """
    Manages hardware devices within the system.
    
    This class is responsible for:
    - Discovering devices in the system
    - Loading and unloading device drivers
    - Managing device state transitions
    - Providing a device registry for the system
    """
    
    def __init__(self):
        self.devices = {}  # Map of device_id to Device objects
        self.device_tree = {}  # Hierarchical organization of devices
        self.driver_registry = {}  # Available device drivers
        self.discovery_handlers = {}  # Handlers for device discovery
        self.event_handlers = {}  # Handlers for device events
        
        # Initialize firmware interface
        self.firmware = FirmwareInterface()
    
    def initialize(self) -> bool:
        """
        Initialize the device manager.
        
        Returns:
            True if initialization was successful, False otherwise.
        """
        logger.info("Initializing hardware device manager...")
        
        try:
            # Initialize firmware interface
            if not self.firmware.initialize():
                logger.error("Failed to initialize firmware interface")
                return False
            
            # Register discovery handlers
            self._register_discovery_handlers()
            
            # Perform initial device discovery
            self._discover_devices()
            
            logger.info(f"Device manager initialized - found {len(self.devices)} devices")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize device manager: {str(e)}")
            return False
    
    def _register_discovery_handlers(self) -> None:
        """Register handlers for discovering different device classes."""
        # CPU discovery
        self.discovery_handlers[DeviceClass.PROCESSOR] = self._discover_processors
        
        # Memory discovery
        self.discovery_handlers[DeviceClass.MEMORY] = self._discover_memory
        
        # Storage discovery
        self.discovery_handlers[DeviceClass.STORAGE] = self._discover_storage
        
        # Network discovery
        self.discovery_handlers[DeviceClass.NETWORK] = self._discover_network
        
        # Display discovery
        self.discovery_handlers[DeviceClass.DISPLAY] = self._discover_display
    
    def _discover_devices(self) -> None:
        """Perform hardware discovery to find all devices in the system."""
        logger.info("Starting hardware discovery...")
        
        # Get system configuration from firmware
        system_config = self.firmware.read_system_config()
        logger.info(f"System information: {system_config}")
        
        # Clear existing devices
        self.devices = {}
        self.device_tree = {}
        
        # Invoke each discovery handler
        for device_class, handler in self.discovery_handlers.items():
            try:
                logger.info(f"Discovering {device_class.name} devices...")
                discovered = handler()
                logger.info(f"Found {len(discovered)} {device_class.name} devices")
                
                # Add discovered devices to registry
                for device in discovered:
                    self.devices[device.device_id] = device
                    
                    # Add to device tree
                    if device.parent:
                        if device.parent in self.devices:
                            self.devices[device.parent].children.append(device.device_id)
                    else:
                        # Root device
                        if device.device_class not in self.device_tree:
                            self.device_tree[device.device_class] = []
                        self.device_tree[device.device_class].append(device.device_id)
                
            except Exception as e:
                logger.error(f"Error discovering {device_class.name} devices: {str(e)}")
    
    def _discover_processors(self) -> List[Device]:
        """Discover CPU/processors in the system."""
        processors = []
        
        # Create a CPU device using platform and os modules
        cpu = Device(
            device_id="CPU0",
            device_class=DeviceClass.PROCESSOR,
            name=platform.processor() or "Unknown CPU",
            vendor="Unknown", # platform module does not provide vendor
            model=platform.processor() or "Unknown"
        )

        # Get core count, fallback to 1 if not available
        try:
            cores = os.cpu_count()
        except NotImplementedError:
            cores = 1
        
        cpu.properties = {
            "cores": cores,
            "threads": cores, # A reasonable assumption if thread count is not available
            "frequency_mhz": 0, # Not available from platform/os
            "architecture": platform.machine(),
            "features": [] # Not available from platform/os
        }
        
        cpu.state = DeviceState.ENABLED
        processors.append(cpu)
        
        return processors
    
    def _discover_memory(self) -> List[Device]:
        """Discover memory devices in the system."""
        memory_devices = []
        
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()

            memtotal_line = [line for line in meminfo.split('\n') if 'MemTotal' in line][0]
            memtotal_kb = int(memtotal_line.split()[1])
            memtotal_bytes = memtotal_kb * 1024

            memory_device = Device(
                device_id="MEM0",
                device_class=DeviceClass.MEMORY,
                name="Main Memory",
                vendor="Unknown",
                model="DRAM"
            )
            
            memory_device.properties = {
                "size_bytes": memtotal_bytes,
                "type": "DRAM",
                "physical_address": 0, # Not easily available
                "ecc": False # Not easily available
            }
            
            memory_device.state = DeviceState.ENABLED
            memory_devices.append(memory_device)

        except (FileNotFoundError, IndexError, ValueError):
            logger.warning("Could not get memory info from /proc/meminfo. Falling back to simulation.")
            # Fallback to the old simulation
            memory_map = self.firmware.get_memory_map()
            usable_regions = self.firmware.get_usable_memory()
            for i, region in enumerate(usable_regions):
                memory_device = Device(
                    device_id=f"MEM{i}",
                    device_class=DeviceClass.MEMORY,
                    name=f"RAM Region {i}",
                    vendor="ClarityOS Simulation",
                    model="Dynamic RAM"
                )
                memory_device.properties = {
                    "size_bytes": region.size_bytes,
                    "type": "DDR4",
                    "physical_address": region.physical_start,
                    "ecc": False
                }
                memory_device.state = DeviceState.ENABLED
                memory_devices.append(memory_device)

        return memory_devices
    
    def _discover_storage(self) -> List[Device]:
        """Discover storage devices in the system."""
        storage_devices = []
        
        try:
            # Use lsblk to get storage device info in JSON format
            result = subprocess.run(
                ['lsblk', '--json', '-o', 'NAME,SIZE,TYPE,MODEL'],
                capture_output=True,
                text=True,
                check=True
            )
            devices = json.loads(result.stdout)['blockdevices']

            for i, device_info in enumerate(devices):
                if device_info.get('type') in ['disk', 'rom']:
                    disk = Device(
                        device_id=f"DISK{i}",
                        device_class=DeviceClass.STORAGE,
                        name=device_info.get('name', f'Storage Device {i}'),
                        vendor="Unknown", # lsblk doesn't easily provide vendor
                        model=device_info.get('model', 'Unknown')
                    )

                    disk.properties = {
                        "size_bytes": int(device_info.get('size', 0)),
                        "type": device_info.get('type', 'UNKNOWN'),
                        "block_size": 4096, # A common default
                        "removable": False # Cannot easily determine this from lsblk
                    }

                    disk.state = DeviceState.ENABLED
                    storage_devices.append(disk)

        except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError, IndexError, ValueError):
            logger.warning("Could not get storage info from lsblk. Falling back to simulation.")
            # Fallback to the old simulation
            disk = Device(
                device_id="DISK0",
                device_class=DeviceClass.STORAGE,
                name="Primary Storage",
                vendor="ClarityOS Simulation",
                model="Virtual SSD"
            )

            disk.properties = {
                "size_bytes": 256 * 1024 * 1024 * 1024,  # 256 GB
                "type": "SSD",
                "block_size": 4096,
                "removable": False
            }

            disk.state = DeviceState.ENABLED
            storage_devices.append(disk)

        return storage_devices
    
    def _discover_network(self) -> List[Device]:
        """Discover network devices in the system."""
        network_devices = []
        
        try:
            # Use `ip -j addr` to get network interface info in JSON format
            result = subprocess.run(
                ['ip', '-j', 'addr'],
                capture_output=True,
                text=True,
                check=True
            )
            interfaces = json.loads(result.stdout)

            for i, iface_info in enumerate(interfaces):
                # Skip the loopback interface
                if iface_info.get('ifname') == 'lo':
                    continue

                nic = Device(
                    device_id=f"NET{i}",
                    device_class=DeviceClass.NETWORK,
                    name=iface_info.get('ifname', f'Network Interface {i}'),
                    vendor="Unknown", # Not easily available from `ip`
                    model="Unknown"
                )

                nic.properties = {
                    "mac_address": iface_info.get('address', '00:00:00:00:00:00'),
                    "speed_mbps": iface_info.get('link_speed'), # May be None
                    "duplex": iface_info.get('duplex'), # May be None
                    "wireless": 'wlan' in iface_info.get('ifname', '')
                }

                nic.state = DeviceState.ENABLED
                network_devices.append(nic)

        except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError, IndexError, ValueError):
            logger.warning("Could not get network info from `ip` command. Falling back to simulation.")
            # Fallback to the old simulation
            nic = Device(
                device_id="NET0",
                device_class=DeviceClass.NETWORK,
                name="Primary Network Interface",
                vendor="ClarityOS Simulation",
                model="Virtual Ethernet"
            )

            nic.properties = {
                "mac_address": "00:11:22:33:44:55",
                "speed_mbps": 1000,
                "duplex": "full",
                "wireless": False
            }

            nic.state = DeviceState.ENABLED
            network_devices.append(nic)

        return network_devices
    
    def _discover_display(self) -> List[Device]:
        """Discover display devices in the system."""
        # In a real implementation, this would enumerate graphics cards, 
        # monitors, and other display devices
        
        # For simulation, create a basic display device
        display_devices = []
        
        # Create a simulated display device
        display = Device(
            device_id="DISP0",
            device_class=DeviceClass.DISPLAY,
            name="Primary Display",
            vendor="ClarityOS Simulation",
            model="Virtual Display"
        )
        
        display.properties = {
            "resolution_width": 1920,
            "resolution_height": 1080,
            "color_depth": 32,
            "refresh_rate": 60
        }
        
        display.state = DeviceState.ENABLED
        display_devices.append(display)
        
        return display_devices
    
    def get_devices_by_class(self, device_class: DeviceClass) -> List[Device]:
        """
        Get all devices of a specific class.
        
        Args:
            device_class: The class of devices to retrieve
            
        Returns:
            List of devices of the specified class
        """
        return [dev for dev in self.devices.values() if dev.device_class == device_class]
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """
        Get a device by its ID.
        
        Args:
            device_id: The ID of the device to retrieve
            
        Returns:
            The device if found, None otherwise
        """
        return self.devices.get(device_id)
    
    def print_device_tree(self) -> None:
        """Print the device tree for debugging purposes."""
        logger.info("Device Tree:")
        logger.info("=" * 80)
        
        for device_class, device_ids in self.device_tree.items():
            logger.info(f"{device_class.name}:")
            for device_id in device_ids:
                device = self.devices[device_id]
                logger.info(f"  - {device}")
                self._print_device_children(device, 4)
        
        logger.info("=" * 80)
    
    def _print_device_children(self, device: Device, indent: int) -> None:
        """Recursively print device children."""
        for child_id in device.children:
            if child_id in self.devices:
                child = self.devices[child_id]
                logger.info(f"{' ' * indent}- {child}")
                self._print_device_children(child, indent + 2)

class HardwareAbstractionLayer:
    """
    The Hardware Abstraction Layer (HAL) for ClarityOS.
    
    This class provides a unified interface for interacting with hardware,
    abstracting the differences between various hardware platforms and devices.
    It serves as the primary interface between the operating system and the
    underlying hardware.
    """
    
    def __init__(self):
        # Initialize device manager
        self.device_manager = DeviceManager()
        
        # System resources
        self.io_ports = {}
        self.memory_regions = {}
        self.interrupts = {}
        
        # Hardware capability flags
        self.capabilities = {}
        
        # Initialization status
        self.initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the Hardware Abstraction Layer.
        
        Returns:
            True if initialization was successful, False otherwise.
        """
        logger.info("Initializing Hardware Abstraction Layer...")
        
        try:
            # Initialize device manager
            if not self.device_manager.initialize():
                logger.error("Failed to initialize device manager")
                return False
            
            # Detect hardware capabilities
            self._detect_capabilities()
            
            # Map hardware resources
            self._map_resources()
            
            self.initialized = True
            logger.info("Hardware Abstraction Layer initialized successfully")
            
            # Print device tree for debugging
            self.device_manager.print_device_tree()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize HAL: {str(e)}")
            return False
    
    def _detect_capabilities(self) -> None:
        """Detect hardware capabilities of the system."""
        # CPU capabilities
        processors = self.device_manager.get_devices_by_class(DeviceClass.PROCESSOR)
        if processors:
            cpu = processors[0]
            self.capabilities["arch"] = cpu.properties.get("architecture", "unknown")
            self.capabilities["cores"] = cpu.properties.get("cores", 1)
            self.capabilities["features"] = cpu.properties.get("features", [])
        
        # Memory capabilities
        memory_devices = self.device_manager.get_devices_by_class(DeviceClass.MEMORY)
        if memory_devices:
            total_memory = sum(dev.properties.get("size_bytes", 0) for dev in memory_devices)
            self.capabilities["total_memory"] = total_memory
        
        # Storage capabilities
        storage_devices = self.device_manager.get_devices_by_class(DeviceClass.STORAGE)
        if storage_devices:
            total_storage = sum(dev.properties.get("size_bytes", 0) for dev in storage_devices)
            self.capabilities["total_storage"] = total_storage
            self.capabilities["storage_types"] = list(set(dev.properties.get("type") for dev in storage_devices if "type" in dev.properties))
        
        # Display capabilities
        display_devices = self.device_manager.get_devices_by_class(DeviceClass.DISPLAY)
        if display_devices:
            self.capabilities["has_display"] = True
            self.capabilities["max_resolution"] = (
                max(dev.properties.get("resolution_width", 0) for dev in display_devices),
                max(dev.properties.get("resolution_height", 0) for dev in display_devices)
            )
        else:
            self.capabilities["has_display"] = False
        
        # Network capabilities
        network_devices = self.device_manager.get_devices_by_class(DeviceClass.NETWORK)
        self.capabilities["has_network"] = len(network_devices) > 0
    
    def _map_resources(self) -> None:
        """Map hardware resources (I/O ports, memory regions, interrupts)."""
        # In a real implementation, this would enumerate and map hardware resources
        # For simulation, we'll create a basic mapping
        
        # Get memory map from firmware
        memory_map = self.device_manager.firmware.get_memory_map()
        
        # Map memory regions
        for i, region in enumerate(memory_map):
            self.memory_regions[f"region{i}"] = {
                "start": region.physical_start,
                "size": region.size_bytes,
                "type": region.type.name,
                "attributes": region.attributes
            }
        
        # Simulate I/O port mapping
        self.io_ports = {
            "pic": {"base": 0x20, "size": 2},
            "pit": {"base": 0x40, "size": 4},
            "keyboard": {"base": 0x60, "size": 2},
            "rtc": {"base": 0x70, "size": 2},
            "serial1": {"base": 0x3F8, "size": 8},
            "serial2": {"base": 0x2F8, "size": 8}
        }
        
        # Simulate interrupt mapping
        self.interrupts = {
            "timer": 0,
            "keyboard": 1,
            "serial1": 4,
            "serial2": 3,
            "disk": 14,
            "network": 10
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive system information.
        
        Returns:
            Dictionary with system information
        """
        if not self.initialized:
            self.initialize()
        
        # Get firmware info
        firmware_info = self.device_manager.firmware.read_system_config()
        
        # Compile system information
        info = {
            "firmware": firmware_info,
            "capabilities": self.capabilities,
            "devices": {
                dev_class.name: len(self.device_manager.get_devices_by_class(dev_class))
                for dev_class in DeviceClass
                if dev_class != DeviceClass.UNKNOWN and 
                len(self.device_manager.get_devices_by_class(dev_class)) > 0
            },
            "memory": {
                "total_bytes": self.capabilities.get("total_memory", 0),
                "total_mb": self.capabilities.get("total_memory", 0) / (1024 * 1024)
            }
        }
        
        return info
    
    def exit_boot_services(self) -> bool:
        """
        Exit firmware boot services and take full control of hardware.
        
        Returns:
            True if successful, False otherwise.
        """
        logger.info("Exiting boot services and taking control of hardware...")
        
        # Call firmware interface to exit boot services
        return self.device_manager.firmware.exit_boot_services()
    
    def reboot_system(self) -> None:
        """Reboot the system."""
        logger.info("Initiating system reboot...")
        
        # In a real implementation, this would trigger firmware to reboot
        # For simulation, just log the event
        logger.info("System would reboot now in a real implementation")
    
    def shutdown_system(self) -> None:
        """Shut down the system."""
        logger.info("Initiating system shutdown...")
        
        # In a real implementation, this would trigger firmware to shut down
        # For simulation, just log the event
        logger.info("System would shut down now in a real implementation")
