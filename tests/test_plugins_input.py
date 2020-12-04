import os.path
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from streamlink import PluginError, Streamlink
from streamlink.plugin.plugin import UserInputRequester
from streamlink_cli.console import ConsoleUserInputRequester
from tests.plugin.testplugin import TestPlugin as _TestPlugin


class TestPluginUserInput(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    @contextmanager
    def _mock_console_input(self, isatty=True):
        with patch('streamlink_cli.console.sys.stdin.isatty', return_value=isatty):
            mock_console = MagicMock()
            mock_console.ask.return_value = "username"
            mock_console.askpass.return_value = "password"
            yield ConsoleUserInputRequester(mock_console)

    def test_user_input_bad_class(self):
        p = _TestPlugin("http://example.com/stream")
        self.assertRaises(RuntimeError, p.bind, self.session, 'test_plugin', object())

    def test_user_input_not_implemented(self):
        p = _TestPlugin("http://example.com/stream")
        p.bind(self.session, 'test_plugin', UserInputRequester())
        self.assertRaises(PluginError, p.input_ask, 'test')
        self.assertRaises(PluginError, p.input_ask_password, 'test')

    def test_user_input_console(self):
        p = _TestPlugin("http://example.com/stream")
        with self._mock_console_input() as console_input:
            p.bind(self.session, 'test_plugin', console_input)
            self.assertEqual("username", p.input_ask("username"))
            self.assertEqual("password", p.input_ask_password("password"))
            console_input.console.ask.assert_called_with("username: ")
            console_input.console.askpass.assert_called_with("password: ")

    def test_user_input_console_no_tty(self):
        p = _TestPlugin("http://example.com/stream")
        with self._mock_console_input(isatty=False) as console_input:
            p.bind(self.session, 'test_plugin', console_input)
            self.assertRaises(PluginError, p.input_ask, "username")
            self.assertRaises(PluginError, p.input_ask_password, "password")

    def test_set_via_session(self):
        with self._mock_console_input() as console_input:
            session = Streamlink({"user-input-requester": console_input})
            session.load_plugins(os.path.join(os.path.dirname(__file__), "plugin"))

            p = session.resolve_url("http://test.se/channel")
            self.assertEqual("username", p.input_ask("username"))
            self.assertEqual("password", p.input_ask_password("password"))
