"""
Utility functions for the update system.

This module provides common utility functions used across various update system components.
"""

import hashlib
import os
import time
import sys
from typing import Dict, List, Union, Optional, Any, Tuple


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings.
    
    Args:
        version1: First version
        version2: Second version
        
    Returns:
        1 if version1 > version2
        0 if version1 == version2
        -1 if version1 < version2
    """
    v1_parts = [int(x) for x in version1.split(".")]
    v2_parts = [int(x) for x in version2.split(".")]
    
    # Pad with zeros to ensure equal length
    while len(v1_parts) < len(v2_parts):
        v1_parts.append(0)
    while len(v2_parts) < len(v1_parts):
        v2_parts.append(0)
    
    # Compare each part
    for i in range(len(v1_parts)):
        if v1_parts[i] > v2_parts[i]:
            return 1
        elif v1_parts[i] < v2_parts[i]:
            return -1
    
    # Versions are equal
    return 0


def calculate_file_checksum(filepath: str) -> str:
    """
    Calculate SHA256 checksum of a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        SHA256 checksum as hexadecimal string
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    sha256_hash = hashlib.sha256()
    
    with open(filepath, "rb") as f:
        # Read in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def create_backup_filename(component_name: str, version: str) -> str:
    """
    Create a standardized backup filename for a component.
    
    Args:
        component_name: Name of the component
        version: Current version of the component
        
    Returns:
        Backup filename with timestamp
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return f"{component_name}_v{version}_{timestamp}.bak"


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "2 minutes 30 seconds")
    """
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    result = []
    if days > 0:
        result.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        result.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        result.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not result:
        result.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    return " ".join(result)
