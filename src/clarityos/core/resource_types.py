#!/usr/bin/env python3
"""
Resource type definitions for ClarityOS.

This module defines the types of resources that can be managed and allocated
by the resource management system in ClarityOS.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

class ResourceType(Enum):
    """Types of resources that can be managed."""
    CPU = auto()         # CPU cores/threads
    MEMORY = auto()      # Memory in MB
    STORAGE = auto()     # Storage space in MB
    NETWORK = auto()     # Network bandwidth in Mbps
    GPU = auto()         # GPU compute units
    IO = auto()          # I/O operations per second

@dataclass
class ResourceRequest:
    """Request for resource allocation."""
    component_id: str
    resource_type: ResourceType
    requested_amount: float
    priority: 'Priority'
    reason: Optional[str] = None

@dataclass
class ResourceAllocation:
    """Result of a resource allocation request."""
    component_id: str
    resource_type: ResourceType
    requested_amount: float
    allocated_amount: float
    success: bool
    message: str