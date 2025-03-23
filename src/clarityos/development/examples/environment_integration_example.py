"""
Example demonstrating the use of the Development Environment Integration System.

This script shows how ClarityOS can interact with Git repositories, run tests,
and manage its own codebase - essential capabilities for self-programming.
"""

import os
import sys
import logging
from pprint import pprint

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from clarityos.development.environment_integration import EnvironmentIntegrationSystem
from clarityos.development.code_generation import CodeGenerationSystem
from clarityos.development.code_understanding import CodeUnderstandingSystem

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Path to the ClarityOS codebase
    clarityos_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info(f"Initializing with ClarityOS codebase at: {clarityos_path}")
    
    # Initialize the systems
    env_system = EnvironmentIntegrationSystem(clarityos_path)
    
    print("\n----- ClarityOS Development Environment Integration Example -----")
    
    # Example 1: Get repository status
    print("\n1. Getting repository status")
    try:
        status = env_system.git.status()
        print("\nRepository Status:")
        print(f"  Branch: {status['branch']}")
        print(f"  Modified files: {', '.join(status['files']['modified']) or 'None'}")
        print(f"  Untracked files: {', '.join(status['files']['untracked']) or 'None'}")
        print(f"  Has changes: {status['has_changes']}")
    except Exception as e:
        print(f"Error getting repository status: {e}")
    
    # Example 2: Get commit history
    print("\n2. Getting recent commit history")
    try:
        commits = env_system.git.get_log(5)
        print("\nRecent Commits:")
        for commit in commits:
            print(f"  {commit['hash'][:7]} - {commit['author']} - {commit['message']}")
    except Exception as e:
        print(f"Error getting commit history: {e}")
    
    # Example 3: Self-programming demonstration (simulated)
    print("\n3. Self-programming demonstration (simulated)")
    
    # Initialize the Code Understanding and Generation systems
    cus = CodeUnderstandingSystem(clarityos_path)
    cus.initialize()
    cgs = CodeGenerationSystem(cus)
    
    # Generate a utility class
    print("\nGenerating a utility class for future implementation")
    utility_spec = {
        "type": "class",
        "name": "DateTimeUtility",
        "doc": "Utility class for date and time operations.\n\nProvides methods for formatting, parsing, and manipulating dates and times.",
        "methods": [
            {
                "name": "__init__",
                "doc": "Initialize the utility.",
                "body": "self.logger = logging.getLogger(__name__)"
            },
            {
                "name": "format_timestamp",
                "doc": "Format a timestamp into a human-readable string.",
                "parameters": [
                    {"name": "timestamp", "type": "float"},
                    {"name": "format_str", "type": "str", "default": "'%Y-%m-%d %H:%M:%S'"}
                ],
                "return_type": "str",
                "body": "import datetime\ndt = datetime.datetime.fromtimestamp(timestamp)\nreturn dt.strftime(format_str)"
            },
            {
                "name": "get_current_timestamp",
                "doc": "Get the current timestamp.",
                "return_type": "float",
                "body": "import time\nreturn time.time()"
            }
        ]
    }
    
    utility_code = cgs.generate_code(utility_spec)
    
    print("\nGenerated Utility Class:")
    print("------------------------")
    print(utility_code[:500] + "...\n")  # Show just the first 500 characters
    
    # Simulate a full self-programming cycle (without actually committing to the repo)
    print("\nSimulating a complete self-programming cycle:")
    print("1. Analyze existing code to understand patterns")
    print("2. Identify need for a new utility class")
    print("3. Generate the utility class code")
    print("4. Run tests to verify the code works")
    print("5. Commit the code to the repository")
    
    # Example file path for the utility class
    file_path = "examples/generated/datetime_utility.py"
    full_path = os.path.join(clarityos_path, file_path)
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Write the file to demonstrate the capability, but without committing
    print(f"\nWriting utility class to {file_path} (for demonstration only)")
    with open(full_path, 'w') as f:
        f.write(utility_code)
    
    print("\nFile written successfully")
    print("\nIn a real self-programming scenario, ClarityOS would:")
    print("- Run tests on the generated code")
    print("- Commit the changes to the repository")
    print("- Push the changes to a remote repository")
    print("- Monitor the effects of the changes")
    print("- Learn from the results for future code generation")
    
    # Clean up the demonstration file
    print("\nCleaning up demonstration file")
    try:
        os.remove(full_path)
        print("File removed successfully")
    except:
        print("Note: Could not remove the file (it may be used by another process)")
    
    print("\n----- Environment Integration Example Complete -----")
    print("This demonstration shows how ClarityOS can interact with its own")
    print("source code repository, a critical capability for self-programming.")

if __name__ == "__main__":
    main()
