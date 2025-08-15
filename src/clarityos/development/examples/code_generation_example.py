"""
Example demonstrating the use of the Code Generation System.

This script generates code for new ClarityOS components based on specifications
and demonstrates how the system can be used for self-programming.
"""

import os
import sys
import logging

from ..code_understanding import CodeUnderstandingSystem
from ..code_generation import CodeGenerationSystem

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Path to the ClarityOS codebase
    clarityos_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info(f"Initializing with ClarityOS codebase at: {clarityos_path}")
    
    # Initialize the Code Understanding System
    cus = CodeUnderstandingSystem(clarityos_path)
    cus.initialize()
    
    # Initialize the Code Generation System
    cgs = CodeGenerationSystem(cus)
    
    print("\n----- ClarityOS Code Generation Example -----")
    
    # Example 1: Generate a new agent class
    print("\n1. Generating a new Data Analytics Agent")
    agent_code = cgs.generate_component(
        "DataAnalytics", 
        "agent",
        features=["Data Processing", "Statistical Analysis", "Visualization"]
    )
    
    print("\nGenerated Agent Code:")
    print("------------------------")
    print(agent_code[:500] + "...\n")  # Show just the first 500 characters
    
    # Example 2: Generate a utility class
    print("\n2. Generating a utility class for text processing")
    class_spec = {
        "type": "class",
        "name": "TextProcessor",
        "doc": "Utility class for text processing operations.",
        "methods": [
            {
                "name": "__init__",
                "doc": "Initialize the text processor.",
                "parameters": [
                    {"name": "config", "type": "Optional[Dict]", "default": "None"}
                ],
                "body": "self.config = config or {}\nself.logger = logging.getLogger(__name__)"
            },
            {
                "name": "tokenize",
                "doc": "Tokenize text into words.",
                "parameters": [
                    {"name": "text", "type": "str"}
                ],
                "return_type": "List[str]",
                "body": "return text.split()"
            },
            {
                "name": "remove_stopwords",
                "doc": "Remove common stopwords from text.",
                "parameters": [
                    {"name": "text", "type": "str"},
                    {"name": "stopwords", "type": "List[str]", "default": "None"}
                ],
                "return_type": "str",
                "body": "if stopwords is None:\n    stopwords = ['the', 'and', 'is', 'in', 'it', 'of']\n\nwords = self.tokenize(text)\nfiltered_words = [word for word in words if word.lower() not in stopwords]\nreturn ' '.join(filtered_words)"
            }
        ]
    }
    
    utility_code = cgs.generate_code(class_spec)
    print("\nGenerated Utility Class:")
    print("------------------------")
    print(utility_code[:500] + "...\n")  # Show just the first 500 characters
    
    # Example 3: Generate a module with multiple components
    print("\n3. Generating a complete module for system monitoring")
    
    module_spec = {
        "type": "module",
        "doc": "System monitoring module for ClarityOS.\n\nProvides components for monitoring system resources and performance.",
        "imports": [
            "import logging",
            "import time",
            "from typing import Dict, List, Optional, Any",
            "from clarityos.core.message_bus import MessageBus"
        ],
        "content": "# Module-level logger\nlogger = logging.getLogger(__name__)\n\n"
    }
    
    # Add a monitor class to the module
    monitor_class = {
        "type": "class",
        "name": "SystemMonitor",
        "doc": "Monitors system resources and performance.",
        "methods": [
            {
                "name": "__init__",
                "doc": "Initialize the system monitor.",
                "parameters": [
                    {"name": "message_bus", "type": "MessageBus"},
                    {"name": "config", "type": "Optional[Dict]", "default": "None"}
                ],
                "body": "self.message_bus = message_bus\nself.config = config or {}\nself.running = False\nlogger.info('System Monitor initialized')"
            },
            {
                "name": "start_monitoring",
                "doc": "Start the monitoring process.",
                "return_type": "None",
                "body": "self.running = True\nlogger.info('System monitoring started')"
            },
            {
                "name": "stop_monitoring",
                "doc": "Stop the monitoring process.",
                "return_type": "None",
                "body": "self.running = False\nlogger.info('System monitoring stopped')"
            }
        ]
    }
    
    # Generate the class code and add it to the module content
    monitor_class_code = cgs.generate_code(monitor_class)
    module_spec["content"] += monitor_class_code
    
    # Generate the complete module
    module_code = cgs.generate_code(module_spec)
    print("\nGenerated Module Code:")
    print("------------------------")
    print(module_code[:500] + "...\n")  # Show just the first 500 characters
    
    # Example 4: Self-programming demonstration - generate code based on system analysis
    print("\n4. Self-programming demonstration")
    
    # Find existing agents to determine common patterns
    agent_classes = []
    for fqn, cls in cus.get_code_model().classes.items():
        if "agent" in fqn.lower() or (cls.doc and "agent" in cls.doc.lower()):
            agent_classes.append(cls)
    
    if agent_classes:
        print(f"\nFound {len(agent_classes)} existing agent classes for reference")
        
        # Generate a new agent based on patterns from existing agents
        print("\nGenerating a new Semantic Search Agent that follows existing patterns")
        
        search_agent_code = cgs.generate_component(
            "SemanticSearch", 
            "agent",
            features=["Vector Database Integration", "Query Processing", "Result Ranking"]
        )
        
        print("\nGenerated Semantic Search Agent:")
        print("----------------------------------")
        print(search_agent_code[:500] + "...\n")  # Show just the first 500 characters
    else:
        print("\nNo existing agent classes found for reference")
    
    print("\n----- Code Generation Complete -----")
    print("The Code Generation System has successfully demonstrated its capabilities.")
    print("These examples show how ClarityOS can generate code for new components,")
    print("which is a foundation for self-programming capabilities.")

if __name__ == "__main__":
    main()
