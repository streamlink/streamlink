from io import StringIO
import logging
import unittest

from streamlink import logger


class TestLogging(unittest.TestCase):
    @classmethod
    def _new_logger(cls):
        output = StringIO()
        logger.basicConfig(stream=output, format="[{name}][{levelname}] {message}", style="{")
        return logging.getLogger("streamlink.test"), output

    def test_level(self):
        log, output = self._new_logger()
        logger.root.setLevel("info")
        log.debug("test")
        self.assertEqual(output.tell(), 0)

        logger.root.setLevel("debug")
        log.debug("test")
        self.assertNotEqual(output.tell(), 0)

    def test_output(self):
        log, output = self._new_logger()
        logger.root.setLevel("debug")
        log.debug("test")
        self.assertEqual(output.getvalue(), "[test][debug] test\n")

    def test_trace_output(self):
        log, output = self._new_logger()
        logger.root.setLevel("trace")
        log.trace("test")
        self.assertEqual(output.getvalue(), "[test][trace] test\n")

    def test_trace_no_output(self):
        log, output = self._new_logger()
        logger.root.setLevel("debug")
        log.trace("test")
        self.assertEqual(output.getvalue(), "")

    def test_debug_out_at_trace(self):
        log, output = self._new_logger()
        logger.root.setLevel("trace")
        log.debug("test")
        self.assertEqual(output.getvalue(), "[test][debug] test\n")

    def test_log_unicode(self):
        log, output = self._new_logger()
        logger.root.setLevel("info")
        log.info(u"Special Character: Ѩ")
        self.assertEqual(output.getvalue(), u"[test][info] Special Character: Ѩ\n")
