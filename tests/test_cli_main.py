import os.path
import os.path
import tempfile

import streamlink_cli.main
from streamlink_cli.main import resolve_stream_name, check_file_output
from streamlink_cli.output import FileOutput
import unittest
from tests.mock import Mock, patch


class TestCLIMain(unittest.TestCase):
    def test_check_file_output(self):
        streamlink_cli.main.console = Mock()
        self.assertIsInstance(check_file_output("test", False), FileOutput)

    def test_check_file_output_exists(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = console = Mock()
            console.ask.return_value = "y"
            self.assertTrue(os.path.exists(tmpfile.name))
            self.assertIsInstance(check_file_output(tmpfile.name, False), FileOutput)
        finally:
            tmpfile.close()

    def test_check_file_output_exists_force(self):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = console = Mock()
            self.assertTrue(os.path.exists(tmpfile.name))
            self.assertIsInstance(check_file_output(tmpfile.name, True), FileOutput)
        finally:
            tmpfile.close()

    @patch('sys.exit')
    def test_check_file_output_exists_no(self, sys_exit):
        tmpfile = tempfile.NamedTemporaryFile()
        try:
            streamlink_cli.main.console = console = Mock()
            console.ask.return_value = "n"
            self.assertTrue(os.path.exists(tmpfile.name))
            check_file_output(tmpfile.name, False)
            sys_exit.assert_called_with()
        finally:
            tmpfile.close()

    def test_resolve_stream_name(self):
        high = Mock()
        medium = Mock()
        low = Mock()
        streams = {
            "low": low,
            "medium": medium,
            "high": high,
            "worst": low,
            "best": high
        }
        self.assertEqual("high", resolve_stream_name(streams, "best"))
        self.assertEqual("low", resolve_stream_name(streams, "worst"))
        self.assertEqual("medium", resolve_stream_name(streams, "medium"))
        self.assertEqual("high", resolve_stream_name(streams, "high"))
        self.assertEqual("low", resolve_stream_name(streams, "low"))

