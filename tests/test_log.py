# -*- coding: utf-8 -*-
import logging
import unittest
import warnings

from streamlink import logger, Streamlink
from streamlink.compat import is_py2
from streamlink.utils.encoding import maybe_decode
from tests import catch_warnings

if is_py2:
    from io import BytesIO as StringIO
else:
    from io import StringIO


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
        self.assertEqual(maybe_decode(output.getvalue()), u"[test][info] Special Character: Ѩ\n")


class TestDeprecatedLogger(unittest.TestCase):
    def setUp(self):
        warnings.resetwarnings()
        warnings.simplefilter('always', DeprecationWarning)  # turn off filter

    def tearDown(self):
        warnings.simplefilter('default', DeprecationWarning)  # restore filter

    def _new_logger(self):
        output = StringIO()
        manager = logger.Logger()
        manager.set_output(output)
        return manager, output

    @catch_warnings()
    def test_deprecated_level(self):
        manager, output = self._new_logger()

        with warnings.catch_warnings(record=True):
            log = manager.new_module("test_level")
            log.debug("test")
            self.assertEqual(output.tell(), 0)
            manager.set_level("debug")
            log.debug("test")
            self.assertNotEqual(output.tell(), 0)

    @catch_warnings()
    def test_deprecated_output(self):
        manager, output = self._new_logger()

        log = manager.new_module("test_output")
        manager.set_level("debug")
        log.debug("test")
        self.assertEqual(output.getvalue(), "[test_output][debug] test\n")

    @catch_warnings()
    def test_deprecated_session_logger(self):
        session = Streamlink()
        output = StringIO()

        new_log = session.logger.new_module("test")
        session.set_logoutput(output)
        session.set_loglevel("info")

        new_log.info("test1")

        # regular python loggers shouldn't log here
        logging.getLogger("streamlink.test").critical("should not log")
        self.assertEqual(output.getvalue(), "[test][info] test1\n")
