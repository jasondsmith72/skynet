"""
ClarityOS Prototype Main Script

This script demonstrates the working prototype of the AI-bootstrapped operating system.
It initializes the boot loader, hardware bus, and AI learning system.
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

from clarityos.core.message_bus import MessagePriority, system_bus
from clarityos.prototype.boot_loader import AIBootLoader
from clarityos.prototype.hardware_bus import hardware_bus
from clarityos.prototype.learning_agent import LearningAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('prototype_os.log')
    ]
)
logger = logging.getLogger("prototype_main")


class PrototypeSystem:
    """
    Prototype implementation of the AI-bootstrapped operating system.
    
    This class coordinates the various components of the prototype system
    and demonstrates the boot sequence and learning capabilities.
    """
    
    def __init__(self):
        # Configuration
        self.config = self._load_config()
        
        # System components
        self.boot_loader = AIBootLoader()
        self.hardware_bus = hardware_bus
        self.learning_agent = None
        
        # System state
        self._booted = False
        self._shutting_down = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self) -> dict:
        """Load system configuration."""
        default_config = {
            "simulation_mode": True,
            "boot_timeout": 10.0,
            "learning_agent": {
                "max_concurrent_experiments": 3,
                "min_confidence_threshold": 0.7,
                "exploration_factor": 0.3,
                "observation_interval": 5.0
            },
            "demo_length_seconds": 60
        }
        
        config_path = Path("config/prototype_config.json")
        
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    
                # Merge with defaults for missing keys
                for k, v in default_config.items():
                    if k not in config:
                        config[k] = v
                    elif isinstance(v, dict) and isinstance(config[k], dict):
                        for k2, v2 in v.items():
                            if k2 not in config[k]:
                                config[k][k2] = v2
                
                return config
            
            except Exception as e:
                logger.error(f"Error loading config: {str(e)}")
                return default_config
        else:
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return default_config
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        if not self._shutting_down:
            self._shutting_down = True
            logger.info(f"Received signal {sig}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
    
    async def boot(self) -> bool:
        """Boot the prototype system."""
        logger.info("Starting prototype system boot sequence")
        
        try:
            # Start the message bus
            await system_bus.start()
            logger.info("System message bus started")
            
            # Start the hardware bus
            await self.hardware_bus.start()
            logger.info("Hardware bus started")
            
            # Run the boot loader with timeout
            boot_success = await asyncio.wait_for(
                self.boot_loader.boot(),
                timeout=self.config.get("boot_timeout", 10.0)
            )
            
            if not boot_success:
                logger.error("Boot sequence failed")
                return False
            
            # Initialize the learning agent
            learning_agent_id = "primary_learning_agent"
            self.learning_agent = LearningAgent(
                learning_agent_id,
                self.config.get("learning_agent", {})
            )
            
            # Start the learning agent
            await self.learning_agent.start()
            logger.info("Learning agent started")
            
            # Announce system startup
            await system_bus.publish(
                message_type="system.started",
                content={
                    "timestamp": time.time(),
                    "components": [
                        "message_bus",
                        "hardware_bus",
                        "boot_loader",
                        "learning_agent"
                    ]
                },
                source="prototype_system",
                priority=MessagePriority.HIGH
            )
            
            self._booted = True
            logger.info("Prototype system boot sequence completed successfully")
            
            return True
        
        except asyncio.TimeoutError:
            logger.error(f"Boot sequence timed out after {self.config.get('boot_timeout', 10.0)} seconds")
            return False
            
        except Exception as e:
            logger.error(f"Error during boot sequence: {str(e)}", exc_info=True)
            return False
    
    async def shutdown(self):
        """Shutdown the prototype system."""
        if self._shutting_down:
            logger.info("Shutting down prototype system")
            
            # Stop the learning agent
            if self.learning_agent:
                try:
                    await self.learning_agent.stop()
                    logger.info("Learning agent stopped")
                except Exception as e:
                    logger.error(f"Error stopping learning agent: {str(e)}")
            
            # Stop the hardware bus
            try:
                await self.hardware_bus.stop()
                logger.info("Hardware bus stopped")
            except Exception as e:
                logger.error(f"Error stopping hardware bus: {str(e)}")
            
            # Stop the message bus
            try:
                await system_bus.stop()
                logger.info("System message bus stopped")
            except Exception as e:
                logger.error(f"Error stopping message bus: {str(e)}")
            
            logger.info("Prototype system shutdown complete")
            
            # Exit the program
            if sys.platform != "win32":
                os._exit(0)
    
    async def run_demo(self, duration: float = None):
        """Run a demonstration of the system for a specified duration."""
        if not self._booted:
            logger.error("Cannot run demo - system not booted")
            return
        
        # Use default duration if not specified
        if duration is None:
            duration = self.config.get("demo_length_seconds", 60)
        
        logger.info(f"Starting prototype system demo (duration: {duration} seconds)")
        
        # Start the learning agent's main loop
        agent_task = asyncio.create_task(self.learning_agent.run())
        
        try:
            # Wait for the specified duration or until interrupted
            await asyncio.sleep(duration)
            
            # Get status information
            boot_status = await self.boot_loader.get_status()
            
            logger.info("Demo complete")
            logger.info(f"Boot sequence completed in {boot_status['total_duration']:.2f} seconds")
            logger.info(f"System ran for {duration} seconds")
            
            # Learning agent statistics would be printed here
            
        except asyncio.CancelledError:
            logger.info("Demo interrupted")
            
        finally:
            # Cancel the agent task
            agent_task.cancel()
            try:
                await agent_task
            except asyncio.CancelledError:
                pass
            
            # Initiate shutdown
            await self.shutdown()


async def main():
    """Main function to run the prototype system."""
    # Create the prototype system
    system = PrototypeSystem()
    
    # Boot the system
    boot_success = await system.boot()
    
    if boot_success:
        # Run the demo
        await system.run_demo()
    else:
        logger.error("System boot failed, terminating")
        await system.shutdown()


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
