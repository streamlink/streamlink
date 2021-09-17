import os.path
import sys
import unittest

from streamlink.utils.module import load_module

# used in the import test to verify that this module was imported
__test_marker__ = "test_marker"


class TestUtilsModule(unittest.TestCase):
    def test_load_module_non_existent(self):
        self.assertRaises(ImportError, load_module, "non_existent_module", os.path.dirname(__file__))

    def test_load_module(self):
        self.assertEqual(
            sys.modules[__name__].__test_marker__,
            load_module(__name__.split(".")[-1], os.path.dirname(__file__)).__test_marker__
        )
