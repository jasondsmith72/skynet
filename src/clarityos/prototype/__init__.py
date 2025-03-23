"""
ClarityOS Prototype Module

This package contains prototype implementations of components
for the AI-driven operating system.
"""

from .boot_loader import AIBootLoader, BootStage, BootProgress
from .hardware_bus import (
    DeviceType, DeviceState, DeviceCapability, 
    DeviceInterface, HardwareMessageBus, hardware_bus
)
from .learning_models import (
    LearningMode, LearningDomain, Hypothesis,
    Observation, Experiment, KnowledgeItem,
    ComponentTemplate, SystemComponent
)
from .learning_agent import LearningAgent

# Export the key components
__all__ = [
    'AIBootLoader', 'BootStage', 'BootProgress',
    'DeviceType', 'DeviceState', 'DeviceCapability', 
    'DeviceInterface', 'HardwareMessageBus', 'hardware_bus',
    'LearningMode', 'LearningDomain', 'Hypothesis',
    'Observation', 'Experiment', 'KnowledgeItem',
    'ComponentTemplate', 'SystemComponent',
    'LearningAgent'
]
