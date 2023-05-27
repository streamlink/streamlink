import os.path
import sys

import pytest

from streamlink.utils.module import load_module


# used in the import test to verify that this module was imported
__test_marker__ = "test_marker"


class TestUtilsModule:
    def test_load_module_non_existent(self):
        with pytest.raises(ImportError):
            load_module("non_existent_module", os.path.dirname(__file__))

    def test_load_module(self):
        assert load_module(__name__.split(".")[-1], os.path.dirname(__file__)).__test_marker__ \
               == sys.modules[__name__].__test_marker__
