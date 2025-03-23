#!/usr/bin/env python3
"""
System monitoring module for ClarityOS.

This module provides capabilities for monitoring system resources and performance
metrics, including CPU, memory, disk, and network usage.
"""

import os
import logging
import platform
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("SystemMonitor")

@dataclass
class SystemInfo:
    """Information about the system hardware and capabilities."""
    cpu_count: int
    total_memory: int  # In bytes
    disk_space: int    # In bytes
    platform: str
    os_version: str
    hostname: str

@dataclass
class ResourceUsage:
    """Current resource usage metrics."""
    cpu_percent: float      # 0-100%
    memory_percent: float   # 0-100%
    memory_used: int        # In bytes
    disk_percent: float     # 0-100%
    disk_used: int          # In bytes
    network_rx: int         # Bytes received since last check
    network_tx: int         # Bytes transmitted since last check
    timestamp: float        # Unix timestamp

@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    name: str
    user: str
    cpu_percent: float   # 0-100%
    memory_percent: float  # 0-100%
    memory_rss: int      # In bytes
    status: str
    create_time: float   # Unix timestamp

class SystemMonitor:
    """Monitor system resources and performance metrics."""
    
    def __init__(self):
        """Initialize the system monitor."""
        # Set up platform-specific implementations
        self._setup_platform_specific()
        
        # Initialize network tracking
        self._last_net_io = self._get_network_io()
        self._last_net_time = time.time()
    
    def _setup_platform_specific(self):
        """Set up platform-specific implementations."""
        self._platform = platform.system()
        
        # Try to import platform-specific modules
        try:
            import psutil
            self._has_psutil = True
        except ImportError:
            self._has_psutil = False
            logger.warning("psutil module not available, using fallback methods")
    
    def get_system_info(self) -> SystemInfo:
        """Get information about the system hardware and capabilities.
        
        Returns:
            SystemInfo object with system hardware details
        """
        if self._has_psutil:
            import psutil
            return SystemInfo(
                cpu_count=psutil.cpu_count(logical=True),
                total_memory=psutil.virtual_memory().total,
                disk_space=psutil.disk_usage('/').total,
                platform=platform.system(),
                os_version=platform.version(),
                hostname=platform.node()
            )
        else:
            # Fallback implementation using os module
            total_memory = 8 * 1024 * 1024 * 1024  # Default to 8GB
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            total_memory = int(line.split()[1]) * 1024  # Convert KB to bytes
                            break
            except:
                pass
            
            total_disk = 100 * 1024 * 1024 * 1024  # Default to 100GB
            try:
                statvfs = os.statvfs('/')
                total_disk = statvfs.f_frsize * statvfs.f_blocks
            except:
                pass
                
            return SystemInfo(
                cpu_count=os.cpu_count() or 1,
                total_memory=total_memory,
                disk_space=total_disk,
                platform=platform.system(),
                os_version=platform.version(),
                hostname=platform.node()
            )
    
    def get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage metrics.
        
        Returns:
            ResourceUsage object with current usage metrics
        """
        if self._has_psutil:
            import psutil
            
            # Get current network I/O counters
            current_net_io = self._get_network_io()
            current_time = time.time()
            
            # Calculate deltas since last check
            net_rx = current_net_io[0] - self._last_net_io[0]
            net_tx = current_net_io[1] - self._last_net_io[1]
            time_delta = current_time - self._last_net_time
            
            # Update last values
            self._last_net_io = current_net_io
            self._last_net_time = current_time
            
            return ResourceUsage(
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=psutil.virtual_memory().percent,
                memory_used=psutil.virtual_memory().used,
                disk_percent=psutil.disk_usage('/').percent,
                disk_used=psutil.disk_usage('/').used,
                network_rx=net_rx,
                network_tx=net_tx,
                timestamp=time.time()
            )
        else:
            # Fallback implementation
            cpu_percent = self._get_cpu_percent_fallback()
            mem_info = self._get_memory_info_fallback()
            disk_info = self._get_disk_info_fallback()
            
            # Get current network I/O counters
            current_net_io = self._get_network_io()
            current_time = time.time()
            
            # Calculate deltas since last check
            net_rx = current_net_io[0] - self._last_net_io[0]
            net_tx = current_net_io[1] - self._last_net_io[1]
            time_delta = current_time - self._last_net_time
            
            # Update last values
            self._last_net_io = current_net_io
            self._last_net_time = current_time
            
            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_percent=mem_info[0],
                memory_used=mem_info[1],
                disk_percent=disk_info[0],
                disk_used=disk_info[1],
                network_rx=net_rx,
                network_tx=net_tx,
                timestamp=time.time()
            )
    
    def get_process_list(self) -> List[ProcessInfo]:
        """Get information about running processes.
        
        Returns:
            List of ProcessInfo objects for each running process
        """
        if self._has_psutil:
            import psutil
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'memory_info', 'status', 'create_time']):
                try:
                    proc_info = proc.info
                    memory_rss = proc_info.get('memory_info', {}).rss if hasattr(proc_info.get('memory_info', {}), 'rss') else 0
                    
                    processes.append(ProcessInfo(
                        pid=proc_info['pid'],
                        name=proc_info['name'],
                        user=proc_info.get('username', ''),
                        cpu_percent=proc_info['cpu_percent'] or 0.0,
                        memory_percent=proc_info['memory_percent'] or 0.0,
                        memory_rss=memory_rss,
                        status=proc_info['status'],
                        create_time=proc_info.get('create_time', 0.0)
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            return processes
        else:
            # Very basic fallback implementation
            processes = []
            try:
                # This is Linux-specific and very basic
                for pid in os.listdir('/proc'):
                    if pid.isdigit():
                        try:
                            with open(f'/proc/{pid}/stat', 'r') as f:
                                stat = f.read().split()
                                name = stat[1].strip('()')
                                
                                processes.append(ProcessInfo(
                                    pid=int(pid),
                                    name=name,
                                    user='',
                                    cpu_percent=0.0,
                                    memory_percent=0.0,
                                    memory_rss=0,
                                    status='',
                                    create_time=0.0
                                ))
                        except:
                            pass
            except:
                pass
            
            return processes
    
    def _get_network_io(self) -> Tuple[int, int]:
        """Get current network I/O counters.
        
        Returns:
            Tuple of (bytes_received, bytes_sent)
        """
        if self._has_psutil:
            import psutil
            net_io = psutil.net_io_counters()
            return (net_io.bytes_recv, net_io.bytes_sent)
        else:
            # Fallback implementation for Linux
            try:
                with open('/proc/net/dev', 'r') as f:
                    lines = f.readlines()
                
                rx_bytes = 0
                tx_bytes = 0
                
                for line in lines[2:]:  # Skip header lines
                    parts = line.split(':')
                    if len(parts) < 2:
                        continue
                    
                    interface = parts[0].strip()
                    if interface == 'lo':  # Skip loopback
                        continue
                    
                    data = parts[1].split()
                    rx_bytes += int(data[0])  # Received bytes are the first field
                    tx_bytes += int(data[8])  # Transmitted bytes are the ninth field
                
                return (rx_bytes, tx_bytes)
            except:
                return (0, 0)
    
    def _get_cpu_percent_fallback(self) -> float:
        """Fallback method to get CPU usage percentage.
        
        Returns:
            CPU usage percentage (0-100)
        """
        try:
            # Simple method for Linux using /proc/stat
            with open('/proc/stat', 'r') as f:
                cpu_line = f.readline()
            
            # Parse the CPU line
            cpu_parts = cpu_line.split()[1:]
            total = sum(float(x) for x in cpu_parts)
            idle = float(cpu_parts[3])
            
            # Calculate percentage
            return 100.0 * (1.0 - idle / total)
        except:
            # Return a reasonable default if we can't calculate
            return 50.0
    
    def _get_memory_info_fallback(self) -> Tuple[float, int]:
        """Fallback method to get memory usage information.
        
        Returns:
            Tuple of (percent_used, bytes_used)
        """
        try:
            # Linux-specific implementation using /proc/meminfo
            mem_total = 0
            mem_free = 0
            mem_buffers = 0
            mem_cached = 0
            
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        mem_total = int(line.split()[1]) * 1024  # Convert KB to bytes
                    elif 'MemFree' in line:
                        mem_free = int(line.split()[1]) * 1024
                    elif 'Buffers' in line:
                        mem_buffers = int(line.split()[1]) * 1024
                    elif 'Cached' in line:
                        mem_cached = int(line.split()[1]) * 1024
            
            # Calculate used memory (excluding buffers/cache)
            mem_used = mem_total - mem_free - mem_buffers - mem_cached
            
            # Calculate percentage
            percent = 100.0 * mem_used / mem_total if mem_total > 0 else 0.0
            
            return (percent, mem_used)
        except:
            # Return reasonable defaults if we can't calculate
            return (50.0, 4 * 1024 * 1024 * 1024)  # 50%, 4GB
    
    def _get_disk_info_fallback(self) -> Tuple[float, int]:
        """Fallback method to get disk usage information.
        
        Returns:
            Tuple of (percent_used, bytes_used)
        """
        try:
            # Use os.statvfs for disk information
            disk = os.statvfs('/')
            
            # Calculate total and free space
            total = disk.f_blocks * disk.f_frsize
            free = disk.f_bfree * disk.f_frsize
            used = total - free
            
            # Calculate percentage
            percent = 100.0 * used / total if total > 0 else 0.0
            
            return (percent, used)
        except:
            # Return reasonable defaults if we can't calculate
            return (40.0, 40 * 1024 * 1024 * 1024)  # 40%, 40GB