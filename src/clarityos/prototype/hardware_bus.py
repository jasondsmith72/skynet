"""
Hardware Message Bus Extension for ClarityOS

This module extends the ClarityOS message bus to interface with hardware components,
providing a communication layer between AI agents and physical devices.
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable

from clarityos.core.message_bus import MessageBus, MessagePriority, system_bus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Types of hardware devices that can be managed."""
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    DISPLAY = "display"
    INPUT = "input"
    USB = "usb"
    SENSOR = "sensor"
    GPU = "gpu"
    AUDIO = "audio"


class DeviceState(Enum):
    """Possible states for a hardware device."""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class DeviceCapability:
    """Represents a capability provided by a hardware device."""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.parameters = parameters or {}


class DeviceInterface:
    """Base class for hardware device interfaces."""
    
    def __init__(self, device_id: str, device_type: DeviceType):
        self.device_id = device_id
        self.device_type = device_type
        self.state = DeviceState.UNKNOWN
        self.capabilities: Dict[str, DeviceCapability] = {}
        self.properties: Dict[str, Any] = {}
        self.last_error: Optional[str] = None
        
    async def initialize(self) -> bool:
        """Initialize the device interface. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement initialize()")
    
    async def execute(self, command: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a command on the device. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the device."""
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "state": self.state.value,
            "capabilities": [cap.name for cap in self.capabilities.values()],
            "properties": self.properties,
            "last_error": self.last_error
        }


class DeviceNotFoundError(Exception):
    """Exception raised when a device is not found."""
    pass


class HardwareMessageBus:
    """
    Extension of the MessageBus that interfaces with hardware devices.
    
    This class provides a communication layer between AI agents and physical
    hardware, allowing agents to discover and interact with devices through
    a unified message-based interface.
    """
    
    def __init__(self):
        self.hardware_interfaces: Dict[str, DeviceInterface] = {}
        self.device_registry: Dict[DeviceType, List[str]] = {device_type: [] for device_type in DeviceType}
        self._discovery_handlers: Dict[DeviceType, List[Callable]] = {device_type: [] for device_type in DeviceType}
        self._subscription_ids = []
        self._running = False
    
    async def start(self):
        """Start the hardware message bus and subscribe to relevant messages."""
        if self._running:
            return
        
        logger.info("Starting Hardware Message Bus")
        
        # Subscribe to hardware-related messages
        self._subscription_ids.append(
            system_bus.subscribe(
                "hardware.discover",
                self._handle_hardware_discover,
                "hardware_bus"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "hardware.command",
                self._handle_hardware_command,
                "hardware_bus"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "hardware.register",
                self._handle_hardware_register,
                "hardware_bus"
            )
        )
        
        # Initialize discovery handlers
        self._setup_discovery_handlers()
        
        # Run initial hardware discovery
        asyncio.create_task(self._discover_hardware())
        
        self._running = True
        logger.info("Hardware Message Bus started")
    
    async def stop(self):
        """Stop the hardware message bus and unsubscribe from messages."""
        if not self._running:
            return
        
        logger.info("Stopping Hardware Message Bus")
        
        # Unsubscribe from messages
        for subscription_id in self._subscription_ids:
            system_bus.unsubscribe("*", subscription_id)
        
        self._running = False
        logger.info("Hardware Message Bus stopped")
    
    async def register_hardware_interface(self, device_interface: DeviceInterface) -> bool:
        """
        Register a hardware device interface with the bus.
        
        Args:
            device_interface: The device interface to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        if device_interface.device_id in self.hardware_interfaces:
            logger.warning(f"Device with ID {device_interface.device_id} already registered")
            return False
        
        # Initialize the device
        try:
            success = await device_interface.initialize()
            if not success:
                logger.error(f"Failed to initialize device {device_interface.device_id}")
                return False
        except Exception as e:
            logger.error(f"Error initializing device {device_interface.device_id}: {str(e)}")
            return False
        
        # Register the device
        self.hardware_interfaces[device_interface.device_id] = device_interface
        self.device_registry[device_interface.device_type].append(device_interface.device_id)
        
        # Announce new device
        await system_bus.publish(
            message_type="hardware.device.added",
            content={
                "device_id": device_interface.device_id,
                "device_type": device_interface.device_type.value,
                "capabilities": [cap.name for cap in device_interface.capabilities.values()],
                "properties": device_interface.properties
            },
            source="hardware_bus",
            priority=MessagePriority.NORMAL
        )
        
        logger.info(f"Registered device {device_interface.device_id} of type {device_interface.device_type.value}")
        return True
    
    async def send_hardware_command(
        self, 
        device_id: str, 
        command: str, 
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Send a command to a hardware device.
        
        Args:
            device_id: ID of the target device
            command: Command to execute
            data: Optional data for the command
            
        Returns:
            Response from the device
            
        Raises:
            DeviceNotFoundError: If the device is not found
        """
        if device_id not in self.hardware_interfaces:
            raise DeviceNotFoundError(f"No device with ID {device_id}")
        
        device = self.hardware_interfaces[device_id]
        
        try:
            # Update device state
            device.state = DeviceState.BUSY
            
            # Execute the command
            response = await device.execute(command, data or {})
            
            # Update device state
            device.state = DeviceState.READY
            
            return response
        
        except Exception as e:
            # Update device state and error
            device.state = DeviceState.ERROR
            device.last_error = str(e)
            
            logger.error(f"Error executing command {command} on device {device_id}: {str(e)}")
            
            # Return error response
            return {
                "success": False,
                "error": str(e),
                "device_id": device_id,
                "command": command
            }
    
    async def get_devices_by_type(self, device_type: DeviceType) -> List[Dict[str, Any]]:
        """
        Get all devices of a specific type.
        
        Args:
            device_type: Type of devices to retrieve
            
        Returns:
            List of device information dictionaries
        """
        devices = []
        
        for device_id in self.device_registry.get(device_type, []):
            device = self.hardware_interfaces.get(device_id)
            if device:
                status = await device.get_status()
                devices.append(status)
        
        return devices
    
    async def get_all_devices(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get information about all registered devices.
        
        Returns:
            Dictionary mapping device types to lists of device information
        """
        result = {}
        
        for device_type in DeviceType:
            devices = await self.get_devices_by_type(device_type)
            result[device_type.value] = devices
        
        return result
    
    def register_discovery_handler(self, device_type: DeviceType, handler: Callable) -> None:
        """
        Register a handler function for discovering devices of a specific type.
        
        Args:
            device_type: Type of devices the handler can discover
            handler: Async function that discovers devices
        """
        self._discovery_handlers[device_type].append(handler)
    
    async def _discover_hardware(self) -> None:
        """Run hardware discovery using all registered handlers."""
        logger.info("Starting hardware discovery")
        
        discovery_tasks = []
        
        # Create tasks for each device type
        for device_type, handlers in self._discovery_handlers.items():
            for handler in handlers:
                discovery_tasks.append(self._run_discovery_handler(device_type, handler))
        
        # Run all discovery tasks
        if discovery_tasks:
            await asyncio.gather(*discovery_tasks, return_exceptions=True)
        
        logger.info(f"Hardware discovery complete, found {len(self.hardware_interfaces)} devices")
        
        # Announce discovery completion
        await system_bus.publish(
            message_type="hardware.discovery.complete",
            content={
                "device_count": len(self.hardware_interfaces),
                "devices_by_type": {
                    device_type.value: len(device_ids)
                    for device_type, device_ids in self.device_registry.items()
                    if device_ids
                }
            },
            source="hardware_bus",
            priority=MessagePriority.NORMAL
        )
    
    async def _run_discovery_handler(self, device_type: DeviceType, handler: Callable) -> None:
        """
        Run a single discovery handler and process the results.
        
        Args:
            device_type: Type of devices the handler discovers
            handler: Discovery handler function
        """
        try:
            # Call the handler, which should return a list of DeviceInterface objects
            devices = await handler()
            
            # Register each discovered device
            for device in devices:
                if device.device_type == device_type:
                    await self.register_hardware_interface(device)
                else:
                    logger.warning(
                        f"Discovery handler for {device_type.value} returned "
                        f"device of incorrect type: {device.device_type.value}"
                    )
        
        except Exception as e:
            logger.error(f"Error in discovery handler for {device_type.value}: {str(e)}")
    
    def _setup_discovery_handlers(self) -> None:
        """Register built-in discovery handlers for common device types."""
        # In a real implementation, would register actual discovery handlers
        # For now, this is a placeholder
        pass
    
    # Message handlers
    
    async def _handle_hardware_discover(self, message):
        """Handle hardware discovery requests."""
        content = message.content
        
        # Check if specific device type was requested
        if "device_type" in content:
            try:
                device_type = DeviceType(content["device_type"])
                
                # Run discovery for just this device type
                discovery_tasks = []
                for handler in self._discovery_handlers[device_type]:
                    discovery_tasks.append(self._run_discovery_handler(device_type, handler))
                
                if discovery_tasks:
                    await asyncio.gather(*discovery_tasks, return_exceptions=True)
                
                # Get results for this device type
                devices = await self.get_devices_by_type(device_type)
                
                if message.reply_to:
                    await system_bus.publish(
                        message_type=f"{message.message_type}.reply",
                        content={
                            "success": True,
                            "device_type": device_type.value,
                            "devices": devices
                        },
                        source="hardware_bus",
                        reply_to=message.source
                    )
            
            except ValueError:
                # Invalid device type
                if message.reply_to:
                    await system_bus.publish(
                        message_type=f"{message.message_type}.reply",
                        content={
                            "success": False,
                            "error": f"Invalid device type: {content['device_type']}"
                        },
                        source="hardware_bus",
                        reply_to=message.source
                    )
        
        else:
            # Run full discovery
            await self._discover_hardware()
            
            # Get all devices
            all_devices = await self.get_all_devices()
            
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": True,
                        "devices": all_devices
                    },
                    source="hardware_bus",
                    reply_to=message.source
                )
    
    async def _handle_hardware_command(self, message):
        """Handle hardware command requests."""
        content = message.content
        
        try:
            device_id = content["device_id"]
            command = content["command"]
            data = content.get("data", {})
            
            # Execute the command
            response = await self.send_hardware_command(device_id, command, data)
            
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": True,
                        "response": response
                    },
                    source="hardware_bus",
                    reply_to=message.source
                )
        
        except DeviceNotFoundError as e:
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "error": str(e)
                    },
                    source="hardware_bus",
                    reply_to=message.source
                )
        
        except Exception as e:
            logger.error(f"Error handling hardware command: {str(e)}")
            
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "error": f"Error: {str(e)}"
                    },
                    source="hardware_bus",
                    reply_to=message.source
                )
    
    async def _handle_hardware_register(self, message):
        """Handle hardware registration requests."""
        # This would be implemented in a real system to allow
        # external components to register hardware interfaces
        pass


# Create singleton instance
hardware_bus = HardwareMessageBus()
