import unittest
import ctypes

class TestCtypesImport(unittest.TestCase):
    """
    Tests if importing the ctypes library causes a hang.
    """

    def test_import_ctypes(self):
        """
        This test only imports ctypes to see if it hangs.
        """
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
