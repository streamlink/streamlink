import logging
import unittest
from datetime import datetime
from io import StringIO

import freezegun

from streamlink import logger


class TestLogging(unittest.TestCase):
    @classmethod
    def _new_logger(cls, format="[{name}][{levelname}] {message}", style="{", **params):
        output = StringIO()
        logger.basicConfig(stream=output, format=format, style=style, **params)
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

    def test_style_percent(self):
        log, output = self._new_logger(style="%", format="[%(name)s][%(levelname)s] %(message)s")
        logger.root.setLevel("info")
        log.info("test")
        self.assertEqual(output.getvalue(), "[test][info] test\n")

    def test_style_invalid(self):
        with self.assertRaises(ValueError) as cm:
            self._new_logger(style="invalid")
        self.assertEqual(str(cm.exception), "Only {} and % formatting styles are supported")

    def test_datefmt_default(self):
        with freezegun.freeze_time(datetime(2000, 1, 2, 3, 4, 5, 123456), tz_offset=0):
            log, output = self._new_logger(format="[{asctime}][{name}][{levelname}] {message}")
            logger.root.setLevel("info")
            log.info("test")
            self.assertEqual(output.getvalue(), "[03:04:05][test][info] test\n")

    def test_datefmt_custom(self):
        with freezegun.freeze_time(datetime(2000, 1, 2, 3, 4, 5, 123456), tz_offset=0):
            log, output = self._new_logger(format="[{asctime}][{name}][{levelname}] {message}", datefmt="%H:%M:%S.%f")
            logger.root.setLevel("info")
            log.info("test")
            self.assertEqual(output.getvalue(), "[03:04:05.123456][test][info] test\n")
