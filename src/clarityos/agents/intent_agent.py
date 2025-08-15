"""
User Intent Agent for ClarityOS

This agent processes natural language input from users, extracts their intent,
and translates it into system actions. It serves as the primary interface between
humans and the operating system, providing a natural and intuitive way to
interact with the system.
"""

import asyncio
import json
import logging
import time
import uuid
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ..core.message_bus import MessagePriority, system_bus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of user intent the agent can identify."""
    QUERY = "query"                # User wants information
    ACTION = "action"              # User wants to perform an action
    CONFIGURATION = "configuration"  # User wants to change settings
    NAVIGATION = "navigation"      # User wants to move/navigate
    CREATION = "creation"          # User wants to create something
    MODIFICATION = "modification"  # User wants to modify something
    DELETION = "deletion"          # User wants to delete something
    HELP = "help"                  # User wants assistance
    CLARIFICATION = "clarification"  # User is clarifying previous intent
    UNKNOWN = "unknown"            # Intent couldn't be determined


@dataclass
class Intent:
    """Represents a parsed user intent."""
    id: str
    type: IntentType
    confidence: float  # 0.0 to 1.0
    action: str  # Specific action to take
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    raw_input: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class Context:
    """Represents the conversation and system context."""
    user_id: str
    session_id: str
    previous_intents: List[Intent] = field(default_factory=list)
    current_location: str = "/"  # Current location in system (e.g., filesystem path)
    active_application: Optional[str] = None
    system_state: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


class UserIntentAgent:
    """
    Agent responsible for processing natural language input, extracting user intent,
    and translating it into system actions.
    
    This agent serves as the primary interface between users and the OS, allowing
    them to interact with the system in a natural and intuitive way.
    """
    
    def __init__(self, agent_id: str, config: Dict):
        self.agent_id = agent_id
        self.config = config
        
        # Intent history for each user
        self.contexts: Dict[str, Context] = {}
        
        # Configuration
        self.max_history = config.get("max_history", 10)
        self.context_expiration = config.get("context_expiration", 3600)  # seconds
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        
        # Available commands dictionary - in a real system, this would be populated dynamically
        self.available_commands = {}
        
        # Internal state
        self._shutdown_event = asyncio.Event()
        self._subscription_ids = []
    
    async def start(self):
        """Initialize the agent and subscribe to relevant messages."""
        logger.info(f"Starting UserIntentAgent (ID: {self.agent_id})")
        
        # Register message handlers
        self._subscription_ids.append(
            system_bus.subscribe(
                "user.input",
                self._handle_user_input,
                f"intent_agent_{self.agent_id}"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "user.session.start",
                self._handle_session_start,
                f"intent_agent_{self.agent_id}"
            )
        )
        
        self._subscription_ids.append(
            system_bus.subscribe(
                "user.session.end",
                self._handle_session_end,
                f"intent_agent_{self.agent_id}"
            )
        )
        
        # Load available commands
        await self._load_available_commands()
        
        # Report initialization complete
        await system_bus.publish(
            message_type="agent.status.update",
            content={
                "agent_id": self.agent_id,
                "status": "running",
                "message": "User Intent Agent initialized"
            },
            source=f"intent_agent_{self.agent_id}"
        )
    
    async def stop(self):
        """Clean up and stop the agent."""
        logger.info(f"Stopping UserIntentAgent (ID: {self.agent_id})")
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Unsubscribe from messages
        for subscription_id in self._subscription_ids:
            system_bus.unsubscribe("*", subscription_id)
        
        # Report shutdown
        await system_bus.publish(
            message_type="agent.status.update",
            content={
                "agent_id": self.agent_id,
                "status": "stopped",
                "message": "User Intent Agent stopped"
            },
            source=f"intent_agent_{self.agent_id}"
        )
    
    async def run(self):
        """Main agent loop for context cleanup and maintenance."""
        while not self._shutdown_event.is_set():
            try:
                # Clean up expired contexts
                await self._cleanup_expired_contexts()
                
                # Wait for next cleanup cycle (every minute)
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), 60)
                except asyncio.TimeoutError:
                    pass
                
            except Exception as e:
                logger.error(f"Error in UserIntentAgent main loop: {str(e)}", exc_info=True)
                await asyncio.sleep(1.0)
    
    async def _load_available_commands(self):
        """Load available system commands and their patterns."""
        # In a real implementation, this would dynamically discover available commands
        # For now, use a hard-coded set of example commands
        
        self.available_commands = {
            "open": {
                "description": "Open a file or application",
                "parameters": ["target"],
                "examples": ["open file.txt", "open Chrome", "open photo.jpg"]
            },
            "search": {
                "description": "Search for files or content",
                "parameters": ["query", "location"],
                "examples": ["search for sales reports", "find documents about marketing"]
            },
            "create": {
                "description": "Create new files or directories",
                "parameters": ["type", "name", "location"],
                "examples": ["create new text file", "make a folder called Projects"]
            },
            "delete": {
                "description": "Delete files or directories",
                "parameters": ["target"],
                "examples": ["delete old reports", "remove temp folder"]
            },
            "move": {
                "description": "Move files or directories",
                "parameters": ["source", "destination"],
                "examples": ["move report.pdf to Archives", "relocate photos to backup drive"]
            },
            "copy": {
                "description": "Copy files or directories",
                "parameters": ["source", "destination"],
                "examples": ["copy file.txt to backup", "duplicate this document"]
            },
            "help": {
                "description": "Get help with the system",
                "parameters": ["topic"],
                "examples": ["help with file management", "how do I create a folder?"]
            },
            "settings": {
                "description": "View or change system settings",
                "parameters": ["setting", "value"],
                "examples": ["change theme to dark", "adjust volume to 80%"]
            }
        }
        
        logger.info(f"Loaded {len(self.available_commands)} available commands")
    
    async def _cleanup_expired_contexts(self):
        """Clean up expired user contexts."""
        current_time = time.time()
        expired_users = []
        
        for user_id, context in self.contexts.items():
            if current_time - context.last_updated > self.context_expiration:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.contexts[user_id]
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired user contexts")
    
    async def _get_or_create_context(self, user_id: str, session_id: str) -> Context:
        """Get an existing context or create a new one if it doesn't exist."""
        if user_id in self.contexts:
            # Update the session ID if it changed
            if self.contexts[user_id].session_id != session_id:
                self.contexts[user_id].session_id = session_id
                self.contexts[user_id].previous_intents = []
            
            # Update the timestamp
            self.contexts[user_id].last_updated = time.time()
            
            return self.contexts[user_id]
        else:
            # Create a new context
            context = Context(
                user_id=user_id,
                session_id=session_id
            )
            
            self.contexts[user_id] = context
            return context
    
    async def _parse_intent(self, user_input: str, context: Context) -> Intent:
        """
        Parse user input to extract intent.
        
        In a real implementation, this would use an LLM or NLU system.
        This simplified version uses keyword matching.
        """
        # Create a new intent ID
        intent_id = str(uuid.uuid4())
        
        # Default to unknown intent
        intent_type = IntentType.UNKNOWN
        confidence = 0.0
        action = ""
        parameters = {}
        
        # Lowercase the input for easier matching
        input_lower = user_input.lower()
        
        # Simple keyword matching for demo purposes
        # In a real implementation, this would use much more sophisticated NLU
        
        # Check for query intents
        if any(word in input_lower for word in ["what", "where", "when", "who", "how", "why", "?"]):
            intent_type = IntentType.QUERY
            confidence = 0.8
            
            # Determine specific query action
            if "weather" in input_lower:
                action = "get_weather"
                confidence = 0.9
            elif "time" in input_lower:
                action = "get_time"
                confidence = 0.9
            elif "file" in input_lower and "where" in input_lower:
                action = "locate_file"
                confidence = 0.85
                # Extract file name
                # This is a simplistic approach; real implementations would use NER
                words = input_lower.split()
                for i, word in enumerate(words):
                    if word == "file" and i+1 < len(words):
                        parameters["file_name"] = words[i+1]
            else:
                action = "general_query"
                confidence = 0.7
        
        # Check for action intents
        elif any(cmd in input_lower for cmd in self.available_commands.keys()):
            # Find which command was used
            matching_commands = [cmd for cmd in self.available_commands.keys() if cmd in input_lower]
            if matching_commands:
                command = matching_commands[0]  # Take the first match for simplicity
                
                intent_type = IntentType.ACTION
                action = command
                confidence = 0.85
                
                # Process command-specific parameters
                if command == "open":
                    # Try to extract what to open
                    words = input_lower.split()
                    cmd_index = words.index(command)
                    if cmd_index + 1 < len(words):
                        parameters["target"] = " ".join(words[cmd_index+1:])
                        confidence = 0.9
                
                elif command == "search" or command == "find":
                    # Extract search query
                    query_start = input_lower.find(command) + len(command)
                    if "for" in input_lower[query_start:]:
                        query_start = input_lower.find("for", query_start) + 3
                    
                    query = user_input[query_start:].strip()
                    if query:
                        parameters["query"] = query
                        confidence = 0.9
                
                elif command == "create" or command == "make":
                    # Try to extract what to create
                    if "folder" in input_lower or "directory" in input_lower:
                        parameters["type"] = "directory"
                        confidence = 0.9
                        
                        # Try to extract name
                        if "called" in input_lower:
                            name_start = input_lower.find("called") + 6
                            parameters["name"] = user_input[name_start:].strip()
                            confidence = 0.95
                    
                    elif "file" in input_lower:
                        parameters["type"] = "file"
                        confidence = 0.9
                        
                        # Try to extract name
                        if "called" in input_lower:
                            name_start = input_lower.find("called") + 6
                            parameters["name"] = user_input[name_start:].strip()
                            confidence = 0.95
        
        # Check for help intents
        elif "help" in input_lower:
            intent_type = IntentType.HELP
            action = "get_help"
            confidence = 0.9
            
            # Try to extract help topic
            if "with" in input_lower:
                topic_start = input_lower.find("with") + 4
                parameters["topic"] = user_input[topic_start:].strip()
                confidence = 0.95
        
        # Check for configuration intents
        elif any(word in input_lower for word in ["settings", "preferences", "configure", "setup"]):
            intent_type = IntentType.CONFIGURATION
            action = "modify_settings"
            confidence = 0.8
            
            # Try to extract what setting to change
            if "theme" in input_lower:
                parameters["setting"] = "theme"
                
                # Try to extract value
                if "dark" in input_lower:
                    parameters["value"] = "dark"
                    confidence = 0.95
                elif "light" in input_lower:
                    parameters["value"] = "light"
                    confidence = 0.95
            
            elif "volume" in input_lower:
                parameters["setting"] = "volume"
                
                # Try to extract value
                volume_match = re.search(r'(\d+)%', input_lower)
                if volume_match:
                    parameters["value"] = int(volume_match.group(1))
                    confidence = 0.95
        
        # Create the intent object
        intent = Intent(
            id=intent_id,
            type=intent_type,
            confidence=confidence,
            action=action,
            parameters=parameters,
            raw_input=user_input
        )
        
        return intent
    
    async def _execute_intent(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """
        Execute an intent by dispatching appropriate system commands.
        
        Args:
            intent: The parsed intent to execute
            context: The user context
            
        Returns:
            Dictionary with execution results
        """
        # If confidence is too low, request clarification
        if intent.confidence < self.confidence_threshold:
            return {
                "success": False,
                "message": "I'm not sure what you want to do. Can you please clarify?",
                "requires_clarification": True
            }
        
        # Handle different intent types
        if intent.type == IntentType.QUERY:
            return await self._execute_query_intent(intent, context)
        
        elif intent.type == IntentType.ACTION:
            return await self._execute_action_intent(intent, context)
        
        elif intent.type == IntentType.HELP:
            return await self._execute_help_intent(intent, context)
        
        elif intent.type == IntentType.CONFIGURATION:
            return await self._execute_configuration_intent(intent, context)
        
        else:
            return {
                "success": False,
                "message": f"I don't know how to handle {intent.type.value} intents yet."
            }
    
    async def _execute_query_intent(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """Execute a query intent."""
        action = intent.action
        
        if action == "get_weather":
            # In a real implementation, would call a weather service
            return {
                "success": True,
                "message": "It's currently sunny and 72°F."
            }
        
        elif action == "get_time":
            current_time = time.strftime("%I:%M %p")
            return {
                "success": True,
                "message": f"The current time is {current_time}."
            }
        
        elif action == "locate_file":
            file_name = intent.parameters.get("file_name", "")
            if not file_name:
                return {
                    "success": False,
                    "message": "What file are you looking for?"
                }
            
            # In a real implementation, would search the file system
            return {
                "success": True,
                "message": f"I found {file_name} in /home/user/documents/."
            }
        
        else:
            return {
                "success": False,
                "message": "I'm not sure how to answer that question."
            }
    
    async def _execute_action_intent(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """Execute an action intent."""
        action = intent.action
        
        if action == "open":
            target = intent.parameters.get("target", "")
            if not target:
                return {
                    "success": False,
                    "message": "What would you like to open?"
                }
            
            # In a real implementation, would open the file or application
            return {
                "success": True,
                "message": f"Opening {target}."
            }
        
        elif action == "search":
            query = intent.parameters.get("query", "")
            if not query:
                return {
                    "success": False,
                    "message": "What would you like to search for?"
                }
            
            # In a real implementation, would perform the search
            return {
                "success": True,
                "message": f"Searching for '{query}'..."
            }
        
        elif action == "create":
            item_type = intent.parameters.get("type", "")
            name = intent.parameters.get("name", "")
            
            if not item_type:
                return {
                    "success": False,
                    "message": "What would you like to create?"
                }
            
            if not name:
                return {
                    "success": False,
                    "message": f"What would you like to name the new {item_type}?"
                }
            
            # In a real implementation, would create the item
            return {
                "success": True,
                "message": f"Created {item_type} named '{name}'."
            }
        
        else:
            return {
                "success": False,
                "message": f"I don't know how to {action} yet."
            }
    
    async def _execute_help_intent(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """Execute a help intent."""
        topic = intent.parameters.get("topic", "")
        
        if not topic:
            # General help
            commands = ", ".join(self.available_commands.keys())
            return {
                "success": True,
                "message": f"I can help you with these commands: {commands}. What would you like to know more about?"
            }
        
        # Check if the topic matches a command
        matching_commands = [cmd for cmd in self.available_commands.keys() if cmd in topic.lower()]
        if matching_commands:
            command = matching_commands[0]
            cmd_info = self.available_commands[command]
            
            return {
                "success": True,
                "message": f"{command}: {cmd_info['description']}. Example: {cmd_info['examples'][0]}"
            }
        
        return {
            "success": False,
            "message": f"I don't have help information about {topic} yet."
        }
    
    async def _execute_configuration_intent(self, intent: Intent, context: Context) -> Dict[str, Any]:
        """Execute a configuration intent."""
        setting = intent.parameters.get("setting", "")
        value = intent.parameters.get("value", "")
        
        if not setting:
            return {
                "success": False,
                "message": "What setting would you like to change?"
            }
        
        if not value:
            return {
                "success": False,
                "message": f"What would you like to set {setting} to?"
            }
        
        # In a real implementation, would update the setting
        return {
            "success": True,
            "message": f"Updated {setting} to {value}."
        }
    
    # Message handlers
    
    async def _handle_user_input(self, message):
        """Handle user input messages."""
        content = message.content
        
        try:
            user_id = content.get("user_id", "anonymous")
            session_id = content.get("session_id", str(uuid.uuid4()))
            input_text = content.get("text", "")
            
            if not input_text:
                if message.reply_to:
                    await system_bus.publish(
                        message_type=f"{message.message_type}.reply",
                        content={
                            "success": False,
                            "message": "No input provided."
                        },
                        source=f"intent_agent_{self.agent_id}",
                        reply_to=message.source
                    )
                return
            
            # Get or create user context
            context = await self._get_or_create_context(user_id, session_id)
            
            # Parse the input to extract intent
            intent = await self._parse_intent(input_text, context)
            
            # Add to intent history
            context.previous_intents.append(intent)
            if len(context.previous_intents) > self.max_history:
                context.previous_intents = context.previous_intents[-self.max_history:]
            
            # Execute the intent
            result = await self._execute_intent(intent, context)
            
            # Notify about the intent
            await system_bus.publish(
                message_type="user.intent.processed",
                content={
                    "user_id": user_id,
                    "session_id": session_id,
                    "intent_id": intent.id,
                    "intent_type": intent.type.value,
                    "action": intent.action,
                    "confidence": intent.confidence,
                    "result": result
                },
                source=f"intent_agent_{self.agent_id}"
            )
            
            # Reply if requested
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content=result,
                    source=f"intent_agent_{self.agent_id}",
                    reply_to=message.source
                )
        
        except Exception as e:
            logger.error(f"Error processing user input: {str(e)}", exc_info=True)
            
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "message": f"Error processing your request: {str(e)}"
                    },
                    source=f"intent_agent_{self.agent_id}",
                    reply_to=message.source
                )
    
    async def _handle_session_start(self, message):
        """Handle session start notifications."""
        content = message.content
        
        try:
            user_id = content.get("user_id", "anonymous")
            session_id = content.get("session_id", str(uuid.uuid4()))
            
            # Create a new context for this session
            context = await self._get_or_create_context(user_id, session_id)
            
            logger.info(f"Started new session for user {user_id} (session: {session_id})")
            
            # Reply if requested
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": True,
                        "message": "Session started successfully"
                    },
                    source=f"intent_agent_{self.agent_id}",
                    reply_to=message.source
                )
        
        except Exception as e:
            logger.error(f"Error handling session start: {str(e)}", exc_info=True)
            
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "message": f"Error starting session: {str(e)}"
                    },
                    source=f"intent_agent_{self.agent_id}",
                    reply_to=message.source
                )
    
    async def _handle_session_end(self, message):
        """Handle session end notifications."""
        content = message.content
        
        try:
            user_id = content.get("user_id", "anonymous")
            session_id = content.get("session_id", "")
            
            # Check if we have this user/session
            if user_id in self.contexts and self.contexts[user_id].session_id == session_id:
                # Clear intent history but keep the context
                self.contexts[user_id].previous_intents = []
                logger.info(f"Ended session for user {user_id} (session: {session_id})")
            
            # Reply if requested
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": True,
                        "message": "Session ended successfully"
                    },
                    source=f"intent_agent_{self.agent_id}",
                    reply_to=message.source
                )
        
        except Exception as e:
            logger.error(f"Error handling session end: {str(e)}", exc_info=True)
            
            if message.reply_to:
                await system_bus.publish(
                    message_type=f"{message.message_type}.reply",
                    content={
                        "success": False,
                        "message": f"Error ending session: {str(e)}"
                    },
                    source=f"intent_agent_{self.agent_id}",
                    reply_to=message.source
                )
