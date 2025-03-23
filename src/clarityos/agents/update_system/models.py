"""
Update System Data Models

This module defines the data models used by the update system components.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union


class UpdatePriority(Enum):
    """Priority levels for system updates."""
    CRITICAL = 5  # Security vulnerabilities, critical bugs
    HIGH = 4      # Important bugs, performance issues
    MEDIUM = 3    # Notable improvements, minor bugs
    LOW = 2       # Small improvements, optimizations
    COSMETIC = 1  # Code style, documentation, non-functional changes


class UpdateStatus(Enum):
    """Status of an update."""
    PENDING = "pending"           # Update is available but not started
    PREPARING = "preparing"       # Preparing for update
    DOWNLOADING = "downloading"   # Downloading update components
    VALIDATING = "validating"     # Validating downloaded components
    APPLYING = "applying"         # Applying the update
    TESTING = "testing"           # Testing the update
    COMPLETED = "completed"       # Update successfully completed
    FAILED = "failed"             # Update failed
    ROLLED_BACK = "rolled_back"   # Update was applied but rolled back


@dataclass
class SystemComponent:
    """Represents a system component that can be updated."""
    name: str
    path: str
    version: str
    checksum: str
    dependencies: List[str] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)
    update_history: List[Dict] = field(default_factory=list)


@dataclass
class UpdatePackage:
    """Represents an update package for a system component."""
    component_name: str
    version: str
    source_url: str
    checksum: str
    changes: List[Dict]
    dependencies: Dict[str, str]
    priority: UpdatePriority
    release_notes: str
    apply_script: Optional[str] = None
    tests: List[Dict] = field(default_factory=list)
    status: UpdateStatus = UpdateStatus.PENDING
