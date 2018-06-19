import unittest
import os.path

from streamlink.plugin.plugin import UserInputRequester
from tests.mock import MagicMock

from streamlink import Streamlink, PluginError
from streamlink_cli.console import ConsoleUserInputRequester
from tests.plugins.testplugin import TestPlugin as _TestPlugin


class TestPluginUserInput(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def _mock_console_input(self):
        mock_console = MagicMock()
        mock_console.ask.return_value = "username"
        mock_console.askpass.return_value = "password"
        return ConsoleUserInputRequester(mock_console)

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
        console_input = self._mock_console_input()
        p.bind(self.session, 'test_plugin', console_input)
        self.assertEquals("username", p.input_ask("username"))
        self.assertEquals("password", p.input_ask_password("password"))
        console_input.console.ask.assert_called_with("username: ")
        console_input.console.askpass.assert_called_with("password: ")

    def test_set_via_session(self):
        session = Streamlink({"user-input-requester": self._mock_console_input()})
        session.load_plugins(os.path.join(os.path.dirname(__file__), "plugins"))

        p = session.resolve_url("http://test.se/channel")
        self.assertEquals("username", p.input_ask("username"))
        self.assertEquals("password", p.input_ask_password("password"))
