import unittest
import sys
import os
import platform

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from src.clarityos.hardware.hal import DeviceManager, DeviceClass

class TestHardwareAbstrationLayer(unittest.TestCase):
    """
    Tests for the Hardware Abstraction Layer.
    """

    def setUp(self):
        self.device_manager = DeviceManager()

    def test_discover_processors(self):
        """
        Tests that the _discover_processors method returns a valid CPU device.
        """
        processors = self.device_manager._discover_processors()

        # Should discover at least one processor
        self.assertGreater(len(processors), 0)

        cpu = processors[0]
        self.assertEqual(cpu.device_class, DeviceClass.PROCESSOR)
        self.assertEqual(cpu.name, platform.processor() or "Unknown CPU")
        self.assertEqual(cpu.model, platform.processor() or "Unknown")
        self.assertEqual(cpu.properties.get('architecture'), platform.machine())

        try:
            cores = os.cpu_count()
        except NotImplementedError:
            cores = 1

        self.assertEqual(cpu.properties.get('cores'), cores)


if __name__ == "__main__":
    unittest.main()
