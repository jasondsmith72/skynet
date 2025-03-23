#!/usr/bin/env python3
"""
Priority definitions for ClarityOS.

This module defines the priority levels used throughout ClarityOS
for scheduling tasks, allocating resources, and managing requests.
"""

from enum import Enum, auto

class Priority(Enum):
    """Priority levels for ClarityOS operations."""
    CRITICAL = auto()   # Highest priority, used for system-critical operations
    HIGH = auto()       # High priority, used for important user-facing or time-sensitive operations
    NORMAL = auto()     # Normal priority, default for most operations
    LOW = auto()        # Low priority, used for background tasks
    IDLE = auto()       # Lowest priority, used only when system is otherwise idle
    
    def __lt__(self, other):
        """Compare priorities, lower enum value = higher priority."""
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented
    
    def __gt__(self, other):
        """Compare priorities, lower enum value = higher priority."""
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
    
    def __le__(self, other):
        """Compare priorities, lower enum value = higher priority."""
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
    
    def __ge__(self, other):
        """Compare priorities, lower enum value = higher priority."""
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented