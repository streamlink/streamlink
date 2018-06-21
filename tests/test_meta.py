import unittest
import warnings

from tests import catch_warnings


class TestMeta(unittest.TestCase):
    """
    Meta tests, to test the tests or test utils
    """
    def test_catch_warnings(self):

        @catch_warnings()
        def _assert_false():
            assert False

        self.assertRaises(AssertionError, _assert_false)

    def test_catch_warnings_record(self):

        @catch_warnings(record=True)
        def _includes_warnings(w):
            def _inner():
                warnings.warn("a warning")

            _inner()
            self.assertEqual(1, len(w))
            return True

        self.assertEqual(True, _includes_warnings())
