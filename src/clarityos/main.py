"""
ClarityOS Main Entry Point

This module serves as the main entry point for ClarityOS, initializing the core
components and starting the system.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Dict, List, Optional

from clarityos.core.agent_manager import agent_manager
from clarityos.core.message_bus import MessagePriority, system_bus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('clarity_os.log')
    ]
)
logger = logging.getLogger(__name__)


class ClarityOS:
    """
    Main class for ClarityOS that coordinates all components and manages the system lifecycle.
    """
    
    def __init__(self):
        # Flag to indicate if the system is shutting down
        self._shutting_down = False
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        if not self._shutting_down:
            self._shutting_down = True
            logger.info(f"Received signal {sig}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
    
    async def startup(self):
        """Initialize and start all system components."""
        logger.info("Starting ClarityOS...")
        
        try:
            # Start the message bus
            await system_bus.start()
            logger.info("System message bus started")
            
            # Start the agent manager
            await agent_manager.start()
            logger.info("Agent manager started")
            
            # Register core system agents
            await self._register_system_agents()
            
            logger.info("ClarityOS startup complete - AI-driven operating system core is running")
            
            # Announce system startup
            await system_bus.publish(
                message_type="system.started",
                content={
                    "timestamp": asyncio.get_event_loop().time(),
                    "version": "0.1.0"
                },
                source="clarity_os",
                priority=MessagePriority.HIGH
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error during startup: {str(e)}", exc_info=True)
            await self.shutdown()
            return False
    
    async def _register_system_agents(self):
        """Register and start the core system agents."""
        # Register the resource manager agent
        resource_agent_config = {
            "history_size": 100,
            "update_interval": 5.0
        }
        
        success, message = await agent_manager.register_agent(
            name="Resource Manager",
            module_path="clarityos.agents.resource_agent.ResourceManagerAgent",
            description="Manages and optimizes system resources",
            config=resource_agent_config,
            auto_start=True
        )
        
        if success:
            logger.info(f"Registered Resource Manager agent: {message}")
        else:
            logger.error(f"Failed to register Resource Manager agent: {message}")
        
        # Register the user intent agent
        intent_agent_config = {
            "max_history": 10,
            "context_expiration": 3600
        }
        
        success, message = await agent_manager.register_agent(
            name="User Intent Agent",
            module_path="clarityos.agents.intent_agent.UserIntentAgent",
            description="Processes and executes user intent",
            config=intent_agent_config,
            auto_start=True
        )
        
        if success:
            logger.info(f"Registered User Intent agent: {message}")
        else:
            logger.error(f"Failed to register User Intent agent: {message}")
    
    async def shutdown(self):
        """Gracefully shut down all system components."""
        if self._shutting_down:
            logger.info("Shutting down ClarityOS...")
            
            # Stop the agent manager
            await agent_manager.stop()
            logger.info("Agent manager stopped")
            
            # Stop the message bus
            await system_bus.stop()
            logger.info("System message bus stopped")
            
            # Announce system shutdown
            logger.info("ClarityOS shutdown complete")
            
            # Exit the program
            if sys.platform != "win32":
                os._exit(0)
    
    async def process_user_input(self, user_id: str, session_id: str, input_text: str) -> Dict:
        """
        Process user input by sending it to the intent agent.
        
        Args:
            user_id: ID of the user
            session_id: ID of the user's session
            input_text: Text input from the user
            
        Returns:
            Dictionary with the processing result
        """
        try:
            # Send the input to the intent agent
            response = await system_bus.request_response(
                message_type="user.input",
                content={
                    "user_id": user_id,
                    "session_id": session_id,
                    "text": input_text
                },
                source="clarity_os",
                timeout=10.0
            )
            
            if response:
                return response.content
            else:
                return {
                    "success": False,
                    "message": "No response from intent agent"
                }
        
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }


async def main():
    """Main entry point for ClarityOS."""
    # Create the OS instance
    os = ClarityOS()
    
    # Start the OS
    success = await os.startup()
    if not success:
        logger.error("Failed to start ClarityOS")
        return
    
    # Keep the program running
    try:
        # In a real implementation, would have a proper input/output mechanism
        # For now, just keep the program running
        while True:
            await asyncio.sleep(1)
    
    except asyncio.CancelledError:
        # Gracefully shutdown
        await os.shutdown()


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
