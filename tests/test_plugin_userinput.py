from unittest.mock import Mock, call, patch

import pytest

from streamlink.exceptions import FatalPluginError
from streamlink.session import Streamlink
from streamlink_cli.console import ConsoleUserInputRequester
from tests.plugin.testplugin import TestPlugin as _TestPlugin


def test_session():
    console_input = ConsoleUserInputRequester(Mock())
    session = Streamlink({"user-input-requester": console_input})
    assert session.get_option("user-input-requester") is console_input


class TestPluginUserInput:
    @pytest.fixture()
    def testplugin(self, session: Streamlink):
        return _TestPlugin(session, "http://example.com/stream")

    @pytest.fixture()
    def console_input(self, request, session: Streamlink):
        isatty: bool = request.param
        with patch("streamlink_cli.console.sys.stdin.isatty", return_value=isatty):
            mock_console = Mock()
            mock_console.ask.return_value = "username"
            mock_console.askpass.return_value = "password"
            console_input = ConsoleUserInputRequester(mock_console)
            session.set_option("user-input-requester", console_input)
            yield console_input

    def test_user_input_not_implemented(self, testplugin: _TestPlugin):
        with pytest.raises(FatalPluginError) as cm:
            testplugin.input_ask("test")
        assert str(cm.value) == "This plugin requires user input, however it is not supported on this platform"

        with pytest.raises(FatalPluginError) as cm:
            testplugin.input_ask_password("test")
        assert str(cm.value) == "This plugin requires user input, however it is not supported on this platform"

    @pytest.mark.parametrize("console_input", [True], indirect=True)
    def test_user_input_console(self, testplugin: _TestPlugin, console_input: ConsoleUserInputRequester):
        assert testplugin.input_ask("username") == "username"
        assert console_input.console.ask.call_args_list == [call("username: ")]

        assert testplugin.input_ask_password("password") == "password"
        assert console_input.console.askpass.call_args_list == [call("password: ")]

    @pytest.mark.parametrize("console_input", [False], indirect=True)
    def test_user_input_console_no_tty(self, testplugin: _TestPlugin, console_input: ConsoleUserInputRequester):
        with pytest.raises(FatalPluginError) as cm:
            testplugin.input_ask("username")
        assert str(cm.value) == "User input error: no TTY available"

        with pytest.raises(FatalPluginError) as cm:
            testplugin.input_ask_password("username")
        assert str(cm.value) == "User input error: no TTY available"
