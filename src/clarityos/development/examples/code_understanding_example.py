"""
Example demonstrating the use of the Code Understanding System.

This script analyzes the ClarityOS codebase and provides insights into its
structure, relationships, and patterns.
"""

import os
import sys
import logging
from pprint import pprint

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from clarityos.development.code_understanding import CodeUnderstandingSystem

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Path to the ClarityOS codebase
    clarityos_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info(f"Analyzing ClarityOS codebase at: {clarityos_path}")
    
    # Initialize the Code Understanding System
    cus = CodeUnderstandingSystem(clarityos_path)
    cus.initialize()
    
    # Get the code model
    code_model = cus.get_code_model()
    
    # Print summary statistics
    print("\n----- ClarityOS Codebase Analysis -----")
    print(f"Total modules: {len(code_model.modules)}")
    print(f"Total classes: {len(code_model.classes)}")
    print(f"Total functions: {len(code_model.functions)}")
    print(f"Total relationships: {len(code_model.relationships)}")
    
    # Print some module details
    print("\n----- Module Overview -----")
    for name, module in sorted(code_model.modules.items())[:5]:  # Show just the first 5
        print(f"\nModule: {name}")
        print(f"  File: {module.file_path}")
        print(f"  Classes: {len(module.classes)}")
        print(f"  Functions: {len(module.functions)}")
        if module.doc:
            doc_summary = module.doc.split("\n")[0] if module.doc else "No documentation"
            print(f"  Summary: {doc_summary}")
    
    if len(code_model.modules) > 5:
        print(f"... and {len(code_model.modules) - 5} more modules")
    
    # Find all agent classes
    print("\n----- Agent Classes -----")
    agent_classes = []
    for fqn, cls in code_model.classes.items():
        if "agent" in fqn.lower() or (cls.doc and "agent" in cls.doc.lower()):
            agent_classes.append(cls)
    
    for cls in sorted(agent_classes, key=lambda c: c.fully_qualified_name)[:5]:  # Show just the first 5
        print(f"\nClass: {cls.fully_qualified_name}")
        print(f"  Base classes: {', '.join(cls.bases) if cls.bases else 'None'}")
        print(f"  Methods: {len(cls.methods)}")
        if cls.doc:
            doc_summary = cls.doc.split("\n")[0] if cls.doc else "No documentation"
            print(f"  Summary: {doc_summary}")
    
    if len(agent_classes) > 5:
        print(f"... and {len(agent_classes) - 5} more agent classes")
    
    # Analyze inheritance relationships
    print("\n----- Inheritance Relationships -----")
    inheritance_count = 0
    for rel in code_model.relationships:
        if rel.relationship_type == "inherits_from":
            inheritance_count += 1
            if inheritance_count <= 5:  # Show just the first 5
                print(f"{rel.source} inherits from {rel.target}")
    
    if inheritance_count > 5:
        print(f"... and {inheritance_count - 5} more inheritance relationships")
    
    # Analyze function call relationships
    print("\n----- Function Call Relationships -----")
    call_count = 0
    for rel in code_model.relationships:
        if rel.relationship_type == "calls":
            call_count += 1
            if call_count <= 5:  # Show just the first 5
                print(f"{rel.source} calls {rel.target}")
    
    if call_count > 5:
        print(f"... and {call_count - 5} more function call relationships")
    
    # Find and analyze a specific component (System Evolution Agent)
    print("\n----- Analysis of System Evolution Agent -----")
    sea_results = cus.find_entity("SystemEvolutionAgent")
    
    if sea_results:
        for entity_type, entity in sea_results:
            if entity_type == "class":
                print(f"Class: {entity.fully_qualified_name}")
                print(f"  Module: {entity.module_name}")
                print(f"  Base classes: {', '.join(entity.bases) if entity.bases else 'None'}")
                print(f"  Methods: {len(entity.methods)}")
                
                # Print methods
                print("\n  Key methods:")
                for method in entity.methods[:5]:  # Show just the first 5
                    print(f"    - {method.name}")
                
                if len(entity.methods) > 5:
                    print(f"    ... and {len(entity.methods) - 5} more methods")
                
                # Find relationships
                print("\n  Relationships:")
                incoming_count = 0
                outgoing_count = 0
                
                for rel in code_model.relationships:
                    if rel.source == entity.fully_qualified_name:
                        outgoing_count += 1
                        if outgoing_count <= 3:  # Show just the first 3
                            print(f"    - {rel.relationship_type} {rel.target}")
                    
                    if rel.target == entity.fully_qualified_name:
                        incoming_count += 1
                        if incoming_count <= 3:  # Show just the first 3
                            print(f"    - {rel.source} {rel.relationship_type} this class")
                
                if outgoing_count > 3:
                    print(f"    ... and {outgoing_count - 3} more outgoing relationships")
                
                if incoming_count > 3:
                    print(f"    ... and {incoming_count - 3} more incoming relationships")
    else:
        print("System Evolution Agent not found in the codebase.")
    
    print("\n----- Analysis Complete -----")
    print("The Code Understanding System has successfully analyzed the ClarityOS codebase.")
    print("This information can be used to enable self-programming capabilities.")

if __name__ == "__main__":
    main()
