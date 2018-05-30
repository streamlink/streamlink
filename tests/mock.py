from __future__ import absolute_import
try:
    from unittest.mock import *
    import unittest.mock as mock
    __all__ = mock.__all__
except ImportError:
    from mock import *
    import mock
    __all__ = mock.__all__
