import logging
import unittest
import warnings

from streamlink import logger, Streamlink
from streamlink.compat import is_py2

# Docs says StringIO is suppose to take non-unicode strings
# but it doesn't, so let's use BytesIO instead there...
from streamlink_cli.main import setup_logging

if is_py2:
    from io import BytesIO as StringIO
else:
    from io import StringIO


class TestSession(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        setup_logging(self.output)
        self.log = logging.getLogger("streamlink.test")
        warnings.simplefilter('always', DeprecationWarning)  # turn off filter

    def tearDown(self):
        warnings.simplefilter('default', DeprecationWarning)  # restore filter

    def test_level(self):
        logger.root.setLevel("info")
        self.log.debug("test")
        self.assertEqual(self.output.tell(), 0)

        logger.root.setLevel("debug")
        self.log.debug("test")
        self.assertNotEqual(self.output.tell(), 0)

    def test_output(self):
        logger.root.setLevel("debug")
        self.output.seek(0)
        self.log.debug("test")
        self.assertEqual(self.output.getvalue(), "[test][debug] test\n")

    def test_trace_output(self):
        logger.root.setLevel("trace")
        self.output.seek(0)
        self.log.trace("test")
        self.assertEqual(self.output.getvalue(), "[test][trace] test\n")

    def test_deprecated_logger(self):
        session = Streamlink()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            session.logger.debug("test")

            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[0].category, DeprecationWarning))

    def test_deprecated_new_module(self):
        session = Streamlink()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            new_log = session.logger.new_module("test2")

            self.assertEqual(len(w), 2)  # accessing deprecated property and deprecated method
            self.assertTrue(issubclass(w[0].category, DeprecationWarning))
            self.assertTrue(issubclass(w[1].category, DeprecationWarning))

        self.assertEqual(new_log.name, "streamlink.test2")

        new_log.set_level("info")
        self.output.seek(0)
        new_log.info("test")
        self.assertEqual(self.output.getvalue(), "[test2][info] test\n")


if __name__ == "__main__":
    unittest.main()
