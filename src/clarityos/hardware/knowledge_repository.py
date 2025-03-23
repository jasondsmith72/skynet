"""
Hardware Knowledge Repository

This module implements a repository for storing and retrieving knowledge about
hardware components. It serves as the central knowledge base for ClarityOS's
understanding of hardware.
"""

import os
import json
import aiofiles
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logger = logging.getLogger(__name__)

class HardwareComponent:
    """
    Represents knowledge about a specific hardware component.
    """
    
    def __init__(self, component_id: str, component_type: str, manufacturer: str, 
                 model: str, specifications: Dict[str, Any] = None):
        self.component_id = component_id
        self.component_type = component_type
        self.manufacturer = manufacturer
        self.model = model
        self.specifications = specifications or {}
        self.behaviors = {}
        self.interfaces = {}
        self.performance_profiles = {}
        self.known_issues = []
        self.learning_history = []
        self.confidence_scores = {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert component information to a dictionary."""
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "specifications": self.specifications,
            "behaviors": self.behaviors,
            "interfaces": self.interfaces,
            "performance_profiles": self.performance_profiles,
            "known_issues": self.known_issues,
            "learning_history": self.learning_history,
            "confidence_scores": self.confidence_scores
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HardwareComponent':
        """Create a component instance from a dictionary."""
        component = cls(
            component_id=data.get("component_id", ""),
            component_type=data.get("component_type", ""),
            manufacturer=data.get("manufacturer", ""),
            model=data.get("model", ""),
            specifications=data.get("specifications", {})
        )
        component.behaviors = data.get("behaviors", {})
        component.interfaces = data.get("interfaces", {})
        component.performance_profiles = data.get("performance_profiles", {})
        component.known_issues = data.get("known_issues", [])
        component.learning_history = data.get("learning_history", [])
        component.confidence_scores = data.get("confidence_scores", {})
        return component
    
    def update_knowledge(self, knowledge_type: str, knowledge_data: Dict[str, Any],
                         source: str, confidence: float) -> None:
        """
        Update component knowledge with new information.
        
        Args:
            knowledge_type: Type of knowledge being updated (behaviors, interfaces, etc.)
            knowledge_data: The new knowledge data
            source: Source of the knowledge (documentation, experiment, etc.)
            confidence: Confidence score for this knowledge (0.0-1.0)
        """
        # Record the update in learning history
        self.learning_history.append({
            "timestamp": str(datetime.now()),
            "knowledge_type": knowledge_type,
            "source": source,
            "confidence": confidence
        })
        
        # Update the specific knowledge type
        if knowledge_type == "specifications":
            self._update_specifications(knowledge_data, confidence)
        elif knowledge_type == "behaviors":
            self._update_behaviors(knowledge_data, confidence)
        elif knowledge_type == "interfaces":
            self._update_interfaces(knowledge_data, confidence)
        elif knowledge_type == "performance_profiles":
            self._update_performance_profiles(knowledge_data, confidence)
        elif knowledge_type == "known_issues":
            self._update_known_issues(knowledge_data, confidence)
            
    def _update_specifications(self, specs: Dict[str, Any], confidence: float) -> None:
        """Update hardware specifications."""
        for key, value in specs.items():
            # Only update if new confidence is higher than existing
            existing_confidence = self.confidence_scores.get(f"specifications.{key}", 0.0)
            if confidence > existing_confidence:
                self.specifications[key] = value
                self.confidence_scores[f"specifications.{key}"] = confidence
                
    def _update_behaviors(self, behaviors: Dict[str, Any], confidence: float) -> None:
        """Update hardware behaviors."""
        for behavior_key, behavior_data in behaviors.items():
            existing_confidence = self.confidence_scores.get(f"behaviors.{behavior_key}", 0.0)
            if confidence > existing_confidence:
                self.behaviors[behavior_key] = behavior_data
                self.confidence_scores[f"behaviors.{behavior_key}"] = confidence
                
    def _update_interfaces(self, interfaces: Dict[str, Any], confidence: float) -> None:
        """Update hardware interfaces."""
        for interface_key, interface_data in interfaces.items():
            existing_confidence = self.confidence_scores.get(f"interfaces.{interface_key}", 0.0)
            if confidence > existing_confidence:
                self.interfaces[interface_key] = interface_data
                self.confidence_scores[f"interfaces.{interface_key}"] = confidence
                
    def _update_performance_profiles(self, profiles: Dict[str, Any], confidence: float) -> None:
        """Update hardware performance profiles."""
        for profile_key, profile_data in profiles.items():
            existing_confidence = self.confidence_scores.get(f"performance_profiles.{profile_key}", 0.0)
            if confidence > existing_confidence:
                self.performance_profiles[profile_key] = profile_data
                self.confidence_scores[f"performance_profiles.{profile_key}"] = confidence
                
    def _update_known_issues(self, issues: List[Dict[str, Any]], confidence: float) -> None:
        """Update hardware known issues."""
        for issue in issues:
            # Check if similar issue already exists
            similar_issues = [i for i in self.known_issues if i.get("issue_id") == issue.get("issue_id")]
            if similar_issues:
                # Update existing issue if new confidence is higher
                for existing_issue in similar_issues:
                    existing_confidence = self.confidence_scores.get(f"known_issues.{issue.get('issue_id')}", 0.0)
                    if confidence > existing_confidence:
                        existing_issue.update(issue)
                        self.confidence_scores[f"known_issues.{issue.get('issue_id')}"] = confidence
            else:
                # Add new issue
                self.known_issues.append(issue)
                self.confidence_scores[f"known_issues.{issue.get('issue_id')}"] = confidence


class HardwareKnowledgeRepository:
    """
    Manages structured knowledge about hardware components and their interactions.
    """
    
    def __init__(self, data_path: str = "data/hardware_knowledge"):
        self.data_path = data_path
        self.components: Dict[str, HardwareComponent] = {}
        self.component_classes: Dict[str, Dict[str, Any]] = {}
        self.interaction_patterns: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self) -> None:
        """Load hardware knowledge from storage."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_path, exist_ok=True)
            
            # Load component classes
            await self._load_component_classes()
            
            # Load interaction patterns
            await self._load_interaction_patterns()
            
            # Load all components
            await self._load_all_components()
            
            logger.info(f"Initialized hardware knowledge repository with {len(self.components)} components")
            
        except Exception as e:
            logger.error(f"Error initializing hardware knowledge repository: {str(e)}")
            raise
            
    async def _load_component_classes(self) -> None:
        """Load component class definitions."""
        class_file = os.path.join(self.data_path, "component_classes.json")
        if os.path.exists(class_file):
            async with aiofiles.open(class_file, 'r') as f:
                content = await f.read()
                self.component_classes = json.loads(content)
        else:
            # Create default component classes
            self.component_classes = {
                "cpu": {
                    "name": "Central Processing Unit",
                    "properties": ["architecture", "cores", "threads", "frequency", "cache"]
                },
                "gpu": {
                    "name": "Graphics Processing Unit",
                    "properties": ["architecture", "memory", "cuda_cores", "frequency"]
                },
                "memory": {
                    "name": "System Memory",
                    "properties": ["type", "capacity", "frequency", "timings"]
                },
                "storage": {
                    "name": "Storage Device",
                    "properties": ["type", "capacity", "interface", "speed"]
                },
                "motherboard": {
                    "name": "Motherboard",
                    "properties": ["chipset", "form_factor", "socket", "expansion_slots"]
                }
            }
            
            # Save default classes
            os.makedirs(os.path.dirname(class_file), exist_ok=True)
            async with aiofiles.open(class_file, 'w') as f:
                await f.write(json.dumps(self.component_classes, indent=2))
                
    async def _load_interaction_patterns(self) -> None:
        """Load interaction pattern definitions."""
        pattern_file = os.path.join(self.data_path, "interaction_patterns.json")
        if os.path.exists(pattern_file):
            async with aiofiles.open(pattern_file, 'r') as f:
                content = await f.read()
                self.interaction_patterns = json.loads(content)
        else:
            # Create default interaction patterns
            self.interaction_patterns = {
                "memory_access": {
                    "name": "Memory Access Pattern",
                    "operations": ["read", "write", "map", "unmap"],
                    "parameters": ["address", "size", "flags"]
                },
                "io_operations": {
                    "name": "I/O Operations",
                    "operations": ["read", "write", "ioctl"],
                    "parameters": ["port", "value", "command"]
                },
                "interrupt_handling": {
                    "name": "Interrupt Handling",
                    "operations": ["register", "enable", "disable", "acknowledge"],
                    "parameters": ["irq", "handler", "flags"]
                }
            }
            
            # Save default patterns
            os.makedirs(os.path.dirname(pattern_file), exist_ok=True)
            async with aiofiles.open(pattern_file, 'w') as f:
                await f.write(json.dumps(self.interaction_patterns, indent=2))
                
    async def _load_all_components(self) -> None:
        """Load all component definitions."""
        components_dir = os.path.join(self.data_path, "components")
        if not os.path.exists(components_dir):
            os.makedirs(components_dir, exist_ok=True)
            return
            
        # Iterate through component files
        for filename in os.listdir(components_dir):
            if filename.endswith(".json"):
                component_file = os.path.join(components_dir, filename)
                try:
                    async with aiofiles.open(component_file, 'r') as f:
                        content = await f.read()
                        component_data = json.loads(content)
                        component = HardwareComponent.from_dict(component_data)
                        self.components[component.component_id] = component
                except Exception as e:
                    logger.error(f"Error loading component from {filename}: {str(e)}")
                    
    async def save_component(self, component: HardwareComponent) -> bool:
        """
        Save a component to storage.
        
        Args:
            component: The component to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            components_dir = os.path.join(self.data_path, "components")
            os.makedirs(components_dir, exist_ok=True)
            
            component_file = os.path.join(components_dir, f"{component.component_id}.json")
            async with aiofiles.open(component_file, 'w') as f:
                await f.write(json.dumps(component.to_dict(), indent=2))
                
            # Update in-memory component
            self.components[component.component_id] = component
            
            return True
        except Exception as e:
            logger.error(f"Error saving component {component.component_id}: {str(e)}")
            return False
            
    async def get_component(self, component_id: str) -> Optional[HardwareComponent]:
        """
        Get a hardware component by ID.
        
        Args:
            component_id: ID of the component
            
        Returns:
            The component if found, None otherwise
        """
        return self.components.get(component_id)
        
    async def find_components(self, 
                              component_type: Optional[str] = None,
                              manufacturer: Optional[str] = None,
                              model: Optional[str] = None,
                              specifications: Optional[Dict[str, Any]] = None) -> List[HardwareComponent]:
        """
        Find components matching the specified criteria.
        
        Args:
            component_type: Type of component
            manufacturer: Component manufacturer
            model: Component model
            specifications: Component specifications to match
            
        Returns:
            List of matching components
        """
        results = []
        
        for component in self.components.values():
            # Check type
            if component_type and component.component_type != component_type:
                continue
                
            # Check manufacturer
            if manufacturer and component.manufacturer != manufacturer:
                continue
                
            # Check model
            if model and component.model != model:
                continue
                
            # Check specifications
            if specifications:
                match = True
                for key, value in specifications.items():
                    if key not in component.specifications or component.specifications[key] != value:
                        match = False
                        break
                        
                if not match:
                    continue
                    
            # If we reach here, component matches criteria
            results.append(component)
            
        return results
        
    async def create_component(self, 
                               component_type: str,
                               manufacturer: str,
                               model: str,
                               specifications: Dict[str, Any]) -> HardwareComponent:
        """
        Create a new hardware component.
        
        Args:
            component_type: Type of component
            manufacturer: Component manufacturer
            model: Component model
            specifications: Component specifications
            
        Returns:
            The created component
        """
        # Generate a unique ID
        component_id = f"{component_type}-{manufacturer}-{model}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create the component
        component = HardwareComponent(
            component_id=component_id,
            component_type=component_type,
            manufacturer=manufacturer,
            model=model,
            specifications=specifications
        )
        
        # Save the component
        await self.save_component(component)
        
        return component
        
    async def update_component_knowledge(self, 
                                         component_id: str,
                                         knowledge_type: str,
                                         knowledge_data: Dict[str, Any],
                                         source: str,
                                         confidence: float) -> bool:
        """
        Update knowledge about a component.
        
        Args:
            component_id: ID of the component
            knowledge_type: Type of knowledge being updated
            knowledge_data: The new knowledge data
            source: Source of the knowledge
            confidence: Confidence score for this knowledge (0.0-1.0)
            
        Returns:
            True if successful, False otherwise
        """
        # Get the component
        component = await self.get_component(component_id)
        if not component:
            logger.error(f"Component not found: {component_id}")
            return False
            
        # Update the component knowledge
        component.update_knowledge(knowledge_type, knowledge_data, source, confidence)
        
        # Save the updated component
        return await self.save_component(component)
        
    async def get_component_knowledge(self, 
                                     component_id: str,
                                     knowledge_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get knowledge about a component.
        
        Args:
            component_id: ID of the component
            knowledge_type: Type of knowledge to retrieve (None for all)
            
        Returns:
            Dictionary with the requested knowledge
        """
        # Get the component
        component = await self.get_component(component_id)
        if not component:
            logger.error(f"Component not found: {component_id}")
            return {}
            
        # Return the requested knowledge
        if knowledge_type == "specifications":
            return component.specifications
        elif knowledge_type == "behaviors":
            return component.behaviors
        elif knowledge_type == "interfaces":
            return component.interfaces
        elif knowledge_type == "performance_profiles":
            return component.performance_profiles
        elif knowledge_type == "known_issues":
            return {"issues": component.known_issues}
        elif knowledge_type == "learning_history":
            return {"history": component.learning_history}
        elif knowledge_type == "confidence_scores":
            return component.confidence_scores
        else:
            # Return all knowledge
            return component.to_dict()
