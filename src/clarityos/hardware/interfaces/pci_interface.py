"""
PCI Interface for ClarityOS.
"""

from .base_interface import HardwareInterface

class PCIInterface(HardwareInterface):
    """
    PCI Interface for ClarityOS.
    """
    def __init__(self):
        super().__init__()
