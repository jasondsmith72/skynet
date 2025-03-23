"""
Experimentation Framework

This module implements a framework for conducting safe experiments with hardware components
in ClarityOS. It enables the AI to learn about hardware through controlled experimentation.
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class ExperimentationFramework:
    """
    Framework for conducting safe experiments with hardware components.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.experiments = {}
        self.results = {}
        self.interface_framework = None
        
    async def initialize(self) -> bool:
        """Initialize the experimentation framework."""
        try:
            from clarityos.hardware.interface_framework import HardwareInterfaceFramework
            
            # Initialize hardware interface framework if not provided
            if 'interface_framework' in self.config:
                self.interface_framework = self.config['interface_framework']
            else:
                self.interface_framework = HardwareInterfaceFramework(
                    self.config.get('interface_config', {})
                )
                await self.interface_framework.initialize()
            
            logger.info("Experimentation framework initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing experimentation framework: {str(e)}")
            return False
    
    async def schedule_experiment(self, 
                                 component_type: str, 
                                 specifications: Dict[str, Any], 
                                 safety_level: str = "high") -> Dict[str, Any]:
        """
        Schedule a hardware experiment.
        
        Args:
            component_type: Type of hardware component
            specifications: Dictionary of component specifications
            safety_level: Level of safety precautions (high, medium, low)
            
        Returns:
            Dictionary with experiment information
        """
        # Generate appropriate experiments for the component
        experiment_plan = await self._generate_experiment_plan(
            component_type, specifications, safety_level
        )
        
        # Validate the safety of the experiment
        safety_validation = await self._validate_experiment_safety(experiment_plan)
        if not safety_validation["safe"]:
            logger.warning(f"Unsafe experiment rejected: {safety_validation['reason']}")
            return {
                "success": False, 
                "error": f"Unsafe experiment: {safety_validation['reason']}"
            }
        
        # Generate a unique experiment ID
        experiment_id = f"exp-{component_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Store the experiment
        self.experiments[experiment_id] = {
            "id": experiment_id,
            "plan": experiment_plan,
            "status": "scheduled",
            "component_type": component_type,
            "specifications": specifications,
            "safety_level": safety_level,
            "created_at": datetime.now().isoformat(),
            "scheduled_steps": [],
            "completed_steps": [],
            "results": {}
        }
        
        # Schedule the experiment steps
        for step in experiment_plan["steps"]:
            self.experiments[experiment_id]["scheduled_steps"].append(step["id"])
        
        logger.info(f"Scheduled experiment {experiment_id} for {component_type} with {len(experiment_plan['steps'])} steps")
        
        return {
            "success": True,
            "experiment_id": experiment_id,
            "component_type": component_type,
            "step_count": len(experiment_plan["steps"]),
            "safety_level": safety_level
        }
    
    async def execute_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        Execute a scheduled experiment.
        
        Args:
            experiment_id: ID of the experiment to execute
            
        Returns:
            Dictionary with execution results
        """
        # Check if experiment exists
        if experiment_id not in self.experiments:
            logger.warning(f"Experiment not found: {experiment_id}")
            return {"success": False, "error": f"Experiment not found: {experiment_id}"}
        
        experiment = self.experiments[experiment_id]
        
        # Update experiment status
        experiment["status"] = "running"
        experiment["started_at"] = datetime.now().isoformat()
        
        logger.info(f"Executing experiment {experiment_id}")
        
        # Execute each step in the experiment
        step_results = []
        for step_id in experiment["scheduled_steps"]:
            # Find the step in the plan
            step = next((s for s in experiment["plan"]["steps"] if s["id"] == step_id), None)
            if not step:
                logger.warning(f"Step not found in experiment plan: {step_id}")
                continue
            
            logger.info(f"Executing experiment step {step_id}: {step['description']}")
            
            try:
                # Execute the step
                step_result = await self._execute_experiment_step(step, experiment)
                
                # Store the result
                experiment["results"][step_id] = step_result
                experiment["completed_steps"].append(step_id)
                
                step_results.append({
                    "step_id": step_id,
                    "success": step_result.get("success", False),
                    "observations": step_result.get("observations", {})
                })
                
                # Check if we should continue or abort
                if step.get("critical", False) and not step_result.get("success", False):
                    logger.warning(f"Critical step {step_id} failed, aborting experiment {experiment_id}")
                    experiment["status"] = "aborted"
                    break
                
            except Exception as e:
                logger.error(f"Error executing experiment step {step_id}: {str(e)}")
                experiment["results"][step_id] = {
                    "success": False,
                    "error": str(e)
                }
                
                if step.get("critical", False):
                    logger.warning(f"Critical step {step_id} failed with exception, aborting experiment {experiment_id}")
                    experiment["status"] = "aborted"
                    break
        
        # Complete the experiment
        if experiment["status"] != "aborted":
            experiment["status"] = "completed"
        
        experiment["completed_at"] = datetime.now().isoformat()
        
        # Process the aggregate results
        aggregate_results = self._process_experiment_results(experiment)
        experiment["aggregate_results"] = aggregate_results
        
        # Store the experiment results
        self.results[experiment_id] = experiment["results"]
        
        logger.info(f"Experiment {experiment_id} {experiment['status']} with {len(experiment['completed_steps'])}/{len(experiment['scheduled_steps'])} steps completed")
        
        return {
            "success": experiment["status"] == "completed",
            "experiment_id": experiment_id,
            "status": experiment["status"],
            "steps_completed": len(experiment["completed_steps"]),
            "steps_total": len(experiment["scheduled_steps"]),
            "results": aggregate_results
        }
    
    async def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get the results of an experiment.
        
        Args:
            experiment_id: ID of the experiment
            
        Returns:
            Dictionary containing experiment results
        """
        # Check if experiment exists
        if experiment_id not in self.experiments:
            logger.warning(f"Experiment not found: {experiment_id}")
            return {"success": False, "error": f"Experiment not found: {experiment_id}"}
        
        experiment = self.experiments[experiment_id]
        
        return {
            "success": True,
            "experiment_id": experiment_id,
            "status": experiment["status"],
            "component_type": experiment["component_type"],
            "steps_completed": len(experiment["completed_steps"]),
            "steps_total": len(experiment["scheduled_steps"]),
            "results": experiment.get("aggregate_results", {}),
            "detailed_results": experiment["results"]
        }
    
    async def _generate_experiment_plan(self, 
                                       component_type: str, 
                                       specifications: Dict[str, Any],
                                       safety_level: str) -> Dict[str, Any]:
        """
        Generate an experiment plan for a specific hardware component.
        
        Args:
            component_type: Type of hardware component
            specifications: Component specifications
            safety_level: Safety level for the experiment
            
        Returns:
            Dictionary containing the experiment plan
        """
        # Different experiment plans based on component type
        if component_type == "cpu":
            return self._generate_cpu_experiment(specifications, safety_level)
        elif component_type == "memory":
            return self._generate_memory_experiment(specifications, safety_level)
        elif component_type == "storage":
            return self._generate_storage_experiment(specifications, safety_level)
        elif component_type == "gpu":
            return self._generate_gpu_experiment(specifications, safety_level)
        else:
            # Default minimal experiment for unknown component types
            return {
                "component_type": component_type,
                "safety_level": safety_level,
                "steps": [
                    {
                        "id": "basic-detection",
                        "description": f"Basic detection of {component_type}",
                        "interface_type": "system",
                        "operation": "detect",
                        "parameters": {"component_type": component_type},
                        "critical": True
                    }
                ]
            }
    
    def _generate_cpu_experiment(self, specifications: Dict[str, Any], safety_level: str) -> Dict[str, Any]:
        """Generate a CPU experiment plan."""
        steps = [
            {
                "id": "cpu-detect",
                "description": "Detect CPU and basic properties",
                "interface_type": "system",
                "operation": "detect",
                "parameters": {"component_type": "cpu"},
                "critical": True
            }
        ]
        
        # Add additional steps based on safety level
        if safety_level in ["medium", "low"]:
            steps.append({
                "id": "cpu-benchmark-light",
                "description": "Light CPU benchmark test",
                "interface_type": "benchmark",
                "operation": "cpu_test",
                "parameters": {"intensity": "light", "duration": 10},
                "critical": False
            })
            
        if safety_level == "low":
            steps.append({
                "id": "cpu-benchmark-stress",
                "description": "CPU stress test",
                "interface_type": "benchmark",
                "operation": "cpu_test",
                "parameters": {"intensity": "high", "duration": 30},
                "critical": False
            })
            
        return {
            "component_type": "cpu",
            "safety_level": safety_level,
            "steps": steps
        }
    
    def _generate_memory_experiment(self, specifications: Dict[str, Any], safety_level: str) -> Dict[str, Any]:
        """Generate a memory experiment plan."""
        steps = [
            {
                "id": "memory-detect",
                "description": "Detect memory and basic properties",
                "interface_type": "system",
                "operation": "detect",
                "parameters": {"component_type": "memory"},
                "critical": True
            }
        ]
        
        # Add additional steps based on safety level
        if safety_level in ["medium", "low"]:
            steps.append({
                "id": "memory-read-test",
                "description": "Memory read performance test",
                "interface_type": "benchmark",
                "operation": "memory_test",
                "parameters": {"type": "read", "size_mb": 100},
                "critical": False
            })
            
        if safety_level == "low":
            steps.append({
                "id": "memory-write-test",
                "description": "Memory write performance test",
                "interface_type": "benchmark",
                "operation": "memory_test",
                "parameters": {"type": "write", "size_mb": 100},
                "critical": False
            })
            
        return {
            "component_type": "memory",
            "safety_level": safety_level,
            "steps": steps
        }
    
    def _generate_storage_experiment(self, specifications: Dict[str, Any], safety_level: str) -> Dict[str, Any]:
        """Generate a storage experiment plan."""
        steps = [
            {
                "id": "storage-detect",
                "description": "Detect storage device and basic properties",
                "interface_type": "system",
                "operation": "detect",
                "parameters": {"component_type": "storage"},
                "critical": True
            }
        ]
        
        # Add additional steps based on safety level
        if safety_level in ["medium", "low"]:
            steps.append({
                "id": "storage-read-test",
                "description": "Storage read performance test",
                "interface_type": "benchmark",
                "operation": "storage_test",
                "parameters": {"type": "read", "size_mb": 10},
                "critical": False
            })
            
        if safety_level == "low":
            steps.append({
                "id": "storage-write-test",
                "description": "Storage write performance test",
                "interface_type": "benchmark",
                "operation": "storage_test",
                "parameters": {"type": "write", "size_mb": 10},
                "critical": False
            })
            
        return {
            "component_type": "storage",
            "safety_level": safety_level,
            "steps": steps
        }
    
    def _generate_gpu_experiment(self, specifications: Dict[str, Any], safety_level: str) -> Dict[str, Any]:
        """Generate a GPU experiment plan."""
        steps = [
            {
                "id": "gpu-detect",
                "description": "Detect GPU and basic properties",
                "interface_type": "system",
                "operation": "detect",
                "parameters": {"component_type": "gpu"},
                "critical": True
            }
        ]
        
        # Add additional steps based on safety level
        if safety_level in ["medium", "low"]:
            steps.append({
                "id": "gpu-info-test",
                "description": "GPU information test",
                "interface_type": "benchmark",
                "operation": "gpu_test",
                "parameters": {"type": "info"},
                "critical": False
            })
            
        if safety_level == "low":
            steps.append({
                "id": "gpu-compute-test",
                "description": "GPU compute test",
                "interface_type": "benchmark",
                "operation": "gpu_test",
                "parameters": {"type": "compute", "intensity": "light"},
                "critical": False
            })
            
        return {
            "component_type": "gpu",
            "safety_level": safety_level,
            "steps": steps
        }
    
    async def _validate_experiment_safety(self, experiment_plan: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate the safety of an experiment plan.
        
        Args:
            experiment_plan: The experiment plan to validate
            
        Returns:
            Dictionary indicating if the plan is safe
        """
        # Check if the component type is supported
        component_type = experiment_plan["component_type"]
        supported_components = ["cpu", "memory", "storage", "gpu", "motherboard", "network"]
        
        if component_type not in supported_components:
            return {
                "safe": False, 
                "reason": f"Unsupported component type: {component_type}"
            }
        
        # Check each step for safety
        for step in experiment_plan["steps"]:
            # Validate interface type
            interface_type = step["interface_type"]
            if interface_type not in ["system", "benchmark", "memory", "io", "pci"]:
                return {
                    "safe": False,
                    "reason": f"Unsupported interface type in step {step['id']}: {interface_type}"
                }
            
            # Validate operation based on interface type
            operation = step["operation"]
            if interface_type == "system" and operation not in ["detect", "info"]:
                return {
                    "safe": False,
                    "reason": f"Unsupported system operation in step {step['id']}: {operation}"
                }
            
            elif interface_type == "benchmark" and not operation.endswith("_test"):
                return {
                    "safe": False,
                    "reason": f"Unsupported benchmark operation in step {step['id']}: {operation}"
                }
            
            elif interface_type == "memory" and operation not in ["read", "write", "map", "unmap"]:
                return {
                    "safe": False,
                    "reason": f"Unsupported memory operation in step {step['id']}: {operation}"
                }
            
            elif interface_type == "io" and operation not in ["read", "write", "ioctl"]:
                return {
                    "safe": False,
                    "reason": f"Unsupported I/O operation in step {step['id']}: {operation}"
                }
                
            # Additional safety checks could be added here
            
        # All checks passed
        return {"safe": True}
    
    async def _execute_experiment_step(self, step: Dict[str, Any], experiment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single experiment step.
        
        Args:
            step: The step to execute
            experiment: The parent experiment
            
        Returns:
            Dictionary with step execution results
        """
        interface_type = step["interface_type"]
        operation = step["operation"]
        parameters = step["parameters"]
        
        logger.info(f"Executing {interface_type}.{operation} with parameters: {parameters}")
        
        # Different execution based on interface type
        if interface_type == "system":
            return await self._execute_system_operation(operation, parameters)
        elif interface_type == "benchmark":
            return await self._execute_benchmark_operation(operation, parameters)
        elif interface_type in ["memory", "io", "pci"]:
            return await self._execute_hardware_operation(interface_type, operation, parameters)
        else:
            logger.warning(f"Unsupported interface type: {interface_type}")
            return {"success": False, "error": f"Unsupported interface type: {interface_type}"}
    
    async def _execute_system_operation(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a system operation.
        
        Args:
            operation: Operation to perform
            parameters: Operation parameters
            
        Returns:
            Dictionary with operation results
        """
        # Simulate system operations
        if operation == "detect":
            component_type = parameters["component_type"]
            # In a real implementation, this would detect actual hardware
            # For now, return simulated data
            return {
                "success": True,
                "component_type": component_type,
                "observations": {
                    "detected": True,
                    "properties": {
                        "model": f"Simulated {component_type.capitalize()}",
                        "vendor": "ClarityOS Simulation"
                    }
                }
            }
        elif operation == "info":
            component_type = parameters["component_type"]
            # Return simulated component info
            return {
                "success": True,
                "component_type": component_type,
                "observations": {
                    "info": {
                        "model": f"Simulated {component_type.capitalize()}",
                        "vendor": "ClarityOS Simulation",
                        "capabilities": ["simulation", "testing"]
                    }
                }
            }
        else:
            logger.warning(f"Unsupported system operation: {operation}")
            return {"success": False, "error": f"Unsupported system operation: {operation}"}
    
    async def _execute_benchmark_operation(self, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a benchmark operation.
        
        Args:
            operation: Operation to perform
            parameters: Operation parameters
            
        Returns:
            Dictionary with operation results
        """
        # Simulate benchmark operations
        if operation == "cpu_test":
            intensity = parameters.get("intensity", "light")
            duration = parameters.get("duration", 10)
            
            # Simulate CPU test with varying duration based on intensity
            await asyncio.sleep(duration * 0.1)  # Scaled down for simulation
            
            # Return simulated results
            return {
                "success": True,
                "observations": {
                    "performance": {
                        "score": 100 * (1 + (0.5 if intensity == "high" else 0.2)),
                        "intensity": intensity,
                        "duration": duration
                    }
                }
            }
        elif operation == "memory_test":
            test_type = parameters.get("type", "read")
            size_mb = parameters.get("size_mb", 100)
            
            # Simulate memory test
            await asyncio.sleep(size_mb * 0.001)  # Scaled down for simulation
            
            # Return simulated results
            return {
                "success": True,
                "observations": {
                    "performance": {
                        f"{test_type}_speed_mb_s": 1000 + (500 if test_type == "read" else 300),
                        "size_mb": size_mb,
                        "latency_ms": 0.5 if test_type == "read" else 0.8
                    }
                }
            }
        elif operation == "storage_test":
            test_type = parameters.get("type", "read")
            size_mb = parameters.get("size_mb", 10)
            
            # Simulate storage test
            await asyncio.sleep(size_mb * 0.01)  # Scaled down for simulation
            
            # Return simulated results
            return {
                "success": True,
                "observations": {
                    "performance": {
                        f"{test_type}_speed_mb_s": 500 + (300 if test_type == "read" else 200),
                        "size_mb": size_mb,
                        "iops": 5000 if test_type == "read" else 3000
                    }
                }
            }
        elif operation == "gpu_test":
            test_type = parameters.get("type", "info")
            intensity = parameters.get("intensity", "light")
            
            # Simulate GPU test
            await asyncio.sleep(0.5)  # Scaled down for simulation
            
            # Return simulated results
            if test_type == "info":
                return {
                    "success": True,
                    "observations": {
                        "info": {
                            "model": "Simulated GPU",
                            "memory_mb": 8192,
                            "compute_units": 64
                        }
                    }
                }
            else:  # compute test
                return {
                    "success": True,
                    "observations": {
                        "performance": {
                            "compute_score": 10000,
                            "fps": 120,
                            "temperature_c": 60 + (10 if intensity == "high" else 0)
                        }
                    }
                }
        else:
            logger.warning(f"Unsupported benchmark operation: {operation}")
            return {"success": False, "error": f"Unsupported benchmark operation: {operation}"}
    
    async def _execute_hardware_operation(self, interface_type: str, operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a direct hardware operation using the interface framework.
        
        Args:
            interface_type: Type of hardware interface
            operation: Operation to perform
            parameters: Operation parameters
            
        Returns:
            Dictionary with operation results
        """
        if not self.interface_framework:
            logger.warning("Hardware interface framework not initialized")
            return {"success": False, "error": "Hardware interface framework not initialized"}
        
        try:
            # Use the interface framework to perform the operation
            result = await self.interface_framework.interact(
                interface_type=interface_type,
                operation=operation,
                parameters=parameters
            )
            
            # Transform the result into observations
            if result.get("success", False):
                return {
                    "success": True,
                    "observations": {
                        "hardware_interaction": {
                            "interface_type": interface_type,
                            "operation": operation,
                            "result": result
                        }
                    }
                }
            else:
                logger.warning(f"Hardware operation failed: {result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": result.get("error", "Hardware operation failed")
                }
                
        except Exception as e:
            logger.error(f"Error executing hardware operation: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_experiment_results(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the results of an experiment to extract useful information.
        
        Args:
            experiment: The experiment with results
            
        Returns:
            Dictionary with processed results
        """
        # Aggregate observations across all steps
        all_observations = {}
        for step_id, result in experiment["results"].items():
            if result.get("success", False) and "observations" in result:
                for category, data in result["observations"].items():
                    if category not in all_observations:
                        all_observations[category] = {}
                    all_observations[category].update(data)
        
        # Extract specific metrics based on component type
        component_type = experiment["component_type"]
        metrics = {}
        
        if component_type == "cpu":
            if "performance" in all_observations:
                perf = all_observations["performance"]
                metrics["cpu_score"] = perf.get("score")
            if "info" in all_observations:
                info = all_observations["info"]
                metrics["model"] = info.get("model")
                metrics["vendor"] = info.get("vendor")
        
        elif component_type == "memory":
            if "performance" in all_observations:
                perf = all_observations["performance"]
                metrics["read_speed_mb_s"] = perf.get("read_speed_mb_s")
                metrics["write_speed_mb_s"] = perf.get("write_speed_mb_s")
                metrics["latency_ms"] = perf.get("latency_ms")
        
        elif component_type == "storage":
            if "performance" in all_observations:
                perf = all_observations["performance"]
                metrics["read_speed_mb_s"] = perf.get("read_speed_mb_s")
                metrics["write_speed_mb_s"] = perf.get("write_speed_mb_s")
                metrics["iops"] = perf.get("iops")
        
        elif component_type == "gpu":
            if "performance" in all_observations:
                perf = all_observations["performance"]
                metrics["compute_score"] = perf.get("compute_score")
                metrics["fps"] = perf.get("fps")
                metrics["temperature_c"] = perf.get("temperature_c")
            if "info" in all_observations:
                info = all_observations["info"]
                metrics["model"] = info.get("model")
                metrics["memory_mb"] = info.get("memory_mb")
                metrics["compute_units"] = info.get("compute_units")
        
        # Return aggregated results
        return {
            "observations": all_observations,
            "metrics": metrics,
            "experiment_id": experiment["id"],
            "component_type": component_type,
            "success": experiment["status"] == "completed"
        }
