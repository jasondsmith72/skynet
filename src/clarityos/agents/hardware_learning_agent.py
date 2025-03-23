"""
Hardware Learning Agent

This module implements the Hardware Learning Agent for ClarityOS, which is responsible
for learning about hardware components through documentation, observation, and interaction.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class HardwareLearningAgent:
    """
    Agent responsible for learning about hardware components through
    various means including documentation, experimentation, and analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.name = "Hardware Learning Agent"
        self.config = config or {}
        
        # Initialize components
        self.knowledge_repo = None
        self.doc_ingestion = None
        self.interface_framework = None
        
        # Track learning tasks
        self.active_tasks = {}
        self.task_history = []
        
        # Define learning strategies
        self.learning_strategies = {
            "documentation": self._learn_from_documentation,
            "observation": self._learn_from_observation,
            "experimentation": self._learn_from_experimentation
        }
    
    async def initialize(self) -> bool:
        """Initialize the agent."""
        try:
            # Import components
            from clarityos.hardware.knowledge_repository import HardwareKnowledgeRepository
            from clarityos.hardware.documentation_ingestion import DocumentationIngestion
            from clarityos.hardware.interface_framework import HardwareInterfaceFramework
            
            # Initialize hardware knowledge repository
            logger.info("Initializing hardware knowledge repository...")
            self.knowledge_repo = HardwareKnowledgeRepository(
                self.config.get("knowledge_repository", {})
            )
            await self.knowledge_repo.initialize()
            
            # Initialize documentation ingestion system
            logger.info("Initializing documentation ingestion system...")
            self.doc_ingestion = DocumentationIngestion(
                self.config.get("documentation_ingestion", {})
            )
            await self.doc_ingestion.initialize()
            
            # Initialize hardware interface framework
            logger.info("Initializing hardware interface framework...")
            self.interface_framework = HardwareInterfaceFramework(
                self.config.get("interface_framework", {})
            )
            await self.interface_framework.initialize()
            
            logger.info("Hardware Learning Agent initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing Hardware Learning Agent: {str(e)}")
            return False
    
    async def handle_message(self, message_type: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message received by the agent.
        
        Args:
            message_type: Type of message
            content: Message content
            
        Returns:
            Response or result
        """
        if message_type == "hardware.detected":
            return await self._handle_hardware_detected(content)
        elif message_type == "hardware.documentation.available":
            return await self._handle_documentation(content)
        elif message_type == "hardware.experiment.result":
            return await self._handle_experiment_result(content)
        elif message_type == "hardware.learn":
            return await self._handle_learn_request(content)
        else:
            logger.warning(f"Unknown message type: {message_type}")
            return {"success": False, "error": f"Unknown message type: {message_type}"}
    
    async def _handle_hardware_detected(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle notification of newly detected hardware.
        
        Args:
            content: Message content with hardware information
            
        Returns:
            Processing result
        """
        logger.info(f"Handling hardware detected message: {content}")
        
        hardware_info = content
        component_type = hardware_info.get("type")
        specifications = hardware_info.get("specifications", {})
        
        if not component_type:
            logger.warning("Hardware detected message missing component type")
            return {"success": False, "error": "Missing component type"}
        
        # Check if we already know about this hardware
        existing_components = await self.knowledge_repo.find_components(
            component_type=component_type,
            specifications=specifications
        )
        
        if existing_components:
            logger.info(f"Hardware component already known: {component_type}")
            
            # Update knowledge if needed
            component = existing_components[0]
            await self._update_component_knowledge(component, hardware_info)
            
            return {
                "success": True,
                "component_id": component.component_id,
                "action": "updated"
            }
        else:
            logger.info(f"New hardware component detected: {component_type}")
            
            # Create a new component entry
            manufacturer = hardware_info.get("manufacturer", "Unknown")
            model = hardware_info.get("model", "Unknown")
            
            new_component = await self.knowledge_repo.create_component(
                component_type=component_type,
                manufacturer=manufacturer,
                model=model,
                specifications=specifications
            )
            
            # Schedule learning tasks for the new component
            await self._schedule_learning_tasks(new_component.component_id, hardware_info)
            
            return {
                "success": True,
                "component_id": new_component.component_id,
                "action": "created"
            }
    
    async def _handle_documentation(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle newly available hardware documentation.
        
        Args:
            content: Message content with documentation information
            
        Returns:
            Processing result
        """
        logger.info(f"Handling hardware documentation message")
        
        # Extract document information
        source = content.get("source", "Unknown")
        content_type = content.get("content_type", "text")
        doc_content = content.get("content", "")
        
        if not doc_content:
            logger.warning("Documentation message contains no content")
            return {"success": False, "error": "No content provided"}
        
        # Process the documentation
        try:
            analysis_result = await self.doc_ingestion.process_documentation(
                source=source,
                content_type=content_type,
                content=doc_content
            )
            
            # Update knowledge repository with new information
            if analysis_result.get("success", False):
                knowledge_updates = []
                
                for comp_type, specs, knowledge in analysis_result.get("extracted_knowledge", []):
                    # Find matching components
                    components = await self.knowledge_repo.find_components(
                        component_type=comp_type,
                        specifications=specs
                    )
                    
                    # Update each matching component
                    for component in components:
                        for knowledge_type, knowledge_data in knowledge.items():
                            if knowledge_data:
                                await self.knowledge_repo.update_component_knowledge(
                                    component_id=component.component_id,
                                    knowledge_type=knowledge_type,
                                    knowledge_data=knowledge_data,
                                    source=f"documentation:{source}",
                                    confidence=0.8  # High confidence for documentation
                                )
                                
                                knowledge_updates.append({
                                    "component_id": component.component_id,
                                    "knowledge_type": knowledge_type
                                })
                                
                                logger.info(f"Updated component {component.component_id} with {knowledge_type} from documentation")
                
                return {
                    "success": True,
                    "updates": knowledge_updates,
                    "source": source
                }
            else:
                logger.warning(f"Failed to extract knowledge from documentation: {analysis_result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": analysis_result.get('error', 'Failed to extract knowledge'),
                    "source": source
                }
                
        except Exception as e:
            logger.error(f"Error processing documentation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "source": source
            }
    
    async def _handle_experiment_result(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle results from hardware experiments.
        
        Args:
            content: Message content with experiment results
            
        Returns:
            Processing result
        """
        logger.info(f"Handling hardware experiment result message")
        
        # Extract experiment information
        component_id = content.get("component_id")
        experiment_type = content.get("experiment_type")
        observed_behavior = content.get("observed_behavior", {})
        confidence = content.get("confidence", 0.6)  # Default moderate confidence for experiments
        
        if not component_id or not experiment_type:
            logger.warning("Experiment result missing required fields")
            return {"success": False, "error": "Missing required fields"}
        
        # Update component knowledge based on experiment results
        try:
            if experiment_type == "behavior":
                await self.knowledge_repo.update_component_knowledge(
                    component_id=component_id,
                    knowledge_type="behaviors",
                    knowledge_data=observed_behavior,
                    source="experiment",
                    confidence=confidence
                )
                
                logger.info(f"Updated component {component_id} with behavior knowledge from experiment")
                
            elif experiment_type == "performance":
                await self.knowledge_repo.update_component_knowledge(
                    component_id=component_id,
                    knowledge_type="performance_profiles",
                    knowledge_data=observed_behavior,
                    source="experiment",
                    confidence=confidence
                )
                
                logger.info(f"Updated component {component_id} with performance knowledge from experiment")
                
            elif experiment_type == "interface":
                await self.knowledge_repo.update_component_knowledge(
                    component_id=component_id,
                    knowledge_type="interfaces",
                    knowledge_data=observed_behavior,
                    source="experiment",
                    confidence=confidence
                )
                
                logger.info(f"Updated component {component_id} with interface knowledge from experiment")
            
            # Schedule follow-up experiments if results were unexpected
            if content.get("unexpected_behavior", False):
                await self._schedule_followup_experiments(component_id, experiment_type, observed_behavior)
                
            return {
                "success": True,
                "component_id": component_id,
                "experiment_type": experiment_type,
                "followup_scheduled": content.get("unexpected_behavior", False)
            }
                
        except Exception as e:
            logger.error(f"Error updating knowledge from experiment: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "component_id": component_id
            }
    
    async def _handle_learn_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a request to learn about hardware.
        
        Args:
            content: Message content with learning request
            
        Returns:
            Processing result
        """
        strategy = content.get("strategy", "all")
        component_id = content.get("component_id")
        component_type = content.get("component_type")
        
        if not component_id and not component_type:
            logger.warning("Learn request missing component identification")
            return {"success": False, "error": "Must specify component_id or component_type"}
        
        # If specific component ID is provided
        if component_id:
            component = await self.knowledge_repo.get_component(component_id)
            if not component:
                logger.warning(f"Component not found: {component_id}")
                return {"success": False, "error": f"Component not found: {component_id}"}
            
            # Apply the requested learning strategy
            if strategy == "all":
                # Apply all learning strategies
                tasks = []
                for strategy_name, strategy_func in self.learning_strategies.items():
                    tasks.append(strategy_func(component))
                
                results = await asyncio.gather(*tasks)
                return {
                    "success": True,
                    "component_id": component_id,
                    "strategies_applied": list(self.learning_strategies.keys()),
                    "results": results
                }
            elif strategy in self.learning_strategies:
                # Apply specific strategy
                result = await self.learning_strategies[strategy](component)
                return {
                    "success": True,
                    "component_id": component_id,
                    "strategy": strategy,
                    "result": result
                }
            else:
                logger.warning(f"Unknown learning strategy: {strategy}")
                return {"success": False, "error": f"Unknown learning strategy: {strategy}"}
        
        # If component type is provided, find all matching components
        elif component_type:
            components = await self.knowledge_repo.find_components(component_type=component_type)
            if not components:
                logger.warning(f"No components found of type: {component_type}")
                return {"success": False, "error": f"No components found of type: {component_type}"}
            
            # Apply requested strategy to all components
            results = []
            for component in components:
                if strategy == "all":
                    for strategy_name, strategy_func in self.learning_strategies.items():
                        result = await strategy_func(component)
                        results.append({
                            "component_id": component.component_id,
                            "strategy": strategy_name,
                            "result": result
                        })
                elif strategy in self.learning_strategies:
                    result = await self.learning_strategies[strategy](component)
                    results.append({
                        "component_id": component.component_id,
                        "strategy": strategy,
                        "result": result
                    })
            
            return {
                "success": True,
                "component_type": component_type,
                "components_processed": len(components),
                "results": results
            }
    
    async def _update_component_knowledge(self, component: Any, hardware_info: Dict[str, Any]) -> None:
        """
        Update knowledge about an existing component.
        
        Args:
            component: The component to update
            hardware_info: New hardware information
        """
        # Update specifications if changed
        specifications = hardware_info.get("specifications", {})
        if specifications:
            await self.knowledge_repo.update_component_knowledge(
                component_id=component.component_id,
                knowledge_type="specifications",
                knowledge_data=specifications,
                source="hardware_detection",
                confidence=0.9  # High confidence for direct hardware detection
            )
            
            logger.info(f"Updated specifications for component {component.component_id}")
    
    async def _schedule_learning_tasks(self, component_id: str, hardware_info: Dict[str, Any]) -> None:
        """
        Schedule tasks to learn about a hardware component.
        
        Args:
            component_id: ID of the component to learn about
            hardware_info: Information about the hardware
        """
        component_type = hardware_info.get("type")
        specifications = hardware_info.get("specifications", {})
        
        # Schedule documentation search
        doc_task = await self.doc_ingestion.schedule_documentation_search(
            component_type=component_type,
            specifications=specifications
        )
        
        # Create observation task
        task_id = f"observation-{component_id}-{len(self.task_history)}"
        observation_task = {
            "id": task_id,
            "type": "observation",
            "component_id": component_id,
            "hardware_info": hardware_info,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }
        
        self.active_tasks[task_id] = observation_task
        self.task_history.append(observation_task)
        
        # Create experiment task
        await self._schedule_basic_experiments(component_id, component_type)
        
        logger.info(f"Scheduled learning tasks for component {component_id}")
    
    async def _schedule_basic_experiments(self, component_id: str, component_type: str) -> None:
        """
        Schedule basic experiments for a component.
        
        Args:
            component_id: ID of the component
            component_type: Type of the component
        """
        # Different experiments based on component type
        experiment_types = []
        
        if component_type == "cpu":
            experiment_types = ["behavior", "performance"]
        elif component_type == "memory":
            experiment_types = ["performance", "reliability"]
        elif component_type == "storage":
            experiment_types = ["performance", "reliability"]
        elif component_type == "gpu":
            experiment_types = ["behavior", "performance"]
        elif component_type == "motherboard":
            experiment_types = ["connectivity", "compatibility"]
        else:
            # Default experiments for unknown component types
            experiment_types = ["behavior"]
        
        # Schedule each experiment
        for exp_type in experiment_types:
            task_id = f"experiment-{exp_type}-{component_id}-{len(self.task_history)}"
            experiment_task = {
                "id": task_id,
                "type": "experiment",
                "experiment_type": exp_type,
                "component_id": component_id,
                "component_type": component_type,
                "status": "scheduled",
                "created_at": datetime.now().isoformat()
            }
            
            self.active_tasks[task_id] = experiment_task
            self.task_history.append(experiment_task)
        
        logger.info(f"Scheduled {len(experiment_types)} basic experiments for {component_type} component {component_id}")
    
    async def _schedule_followup_experiments(self, component_id: str, experiment_type: str, observed_behavior: Dict[str, Any]) -> None:
        """
        Schedule follow-up experiments based on initial results.
        
        Args:
            component_id: ID of the component
            experiment_type: Type of the initial experiment
            observed_behavior: Observed behavior from the initial experiment
        """
        # Get component details
        component = await self.knowledge_repo.get_component(component_id)
        if not component:
            logger.warning(f"Cannot schedule follow-up experiments, component not found: {component_id}")
            return
        
        # Schedule a more focused experiment based on the observed behavior
        task_id = f"followup-{experiment_type}-{component_id}-{len(self.task_history)}"
        followup_task = {
            "id": task_id,
            "type": "experiment",
            "experiment_type": f"followup-{experiment_type}",
            "component_id": component_id,
            "component_type": component.component_type,
            "previous_behavior": observed_behavior,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }
        
        self.active_tasks[task_id] = followup_task
        self.task_history.append(followup_task)
        
        logger.info(f"Scheduled follow-up experiment for {component_id} based on unexpected {experiment_type} behavior")
    
    async def _learn_from_documentation(self, component: Any) -> Dict[str, Any]:
        """
        Learn about a component from documentation.
        
        Args:
            component: The component to learn about
            
        Returns:
            Learning results
        """
        # Schedule a documentation search for this component
        search_result = await self.doc_ingestion.schedule_documentation_search(
            component_type=component.component_type,
            specifications=component.specifications
        )
        
        return {
            "success": True,
            "component_id": component.component_id,
            "task_id": search_result.get("task_id"),
            "message": f"Documentation search scheduled for {component.component_type}"
        }
    
    async def _learn_from_observation(self, component: Any) -> Dict[str, Any]:
        """
        Learn about a component through observation.
        
        Args:
            component: The component to learn about
            
        Returns:
            Learning results
        """
        # Create an observation task
        task_id = f"observation-{component.component_id}-{len(self.task_history)}"
        observation_task = {
            "id": task_id,
            "type": "observation",
            "component_id": component.component_id,
            "component_type": component.component_type,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }
        
        self.active_tasks[task_id] = observation_task
        self.task_history.append(observation_task)
        
        return {
            "success": True,
            "component_id": component.component_id,
            "task_id": task_id,
            "message": f"Observation task scheduled for {component.component_type}"
        }
    
    async def _learn_from_experimentation(self, component: Any) -> Dict[str, Any]:
        """
        Learn about a component through experimentation.
        
        Args:
            component: The component to learn about
            
        Returns:
            Learning results
        """
        # Schedule appropriate experiments
        await self._schedule_basic_experiments(
            component_id=component.component_id,
            component_type=component.component_type
        )
        
        return {
            "success": True,
            "component_id": component.component_id,
            "message": f"Experiments scheduled for {component.component_type}"
        }
