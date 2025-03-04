from unittest.mock import Mock, call

import pytest

from streamlink.exceptions import FatalPluginError
from streamlink.session import Streamlink
from streamlink_cli.console import ConsoleUserInputRequester
from tests.plugin.testplugin import TestPlugin as _TestPlugin


@pytest.fixture()
def console(request: pytest.FixtureRequest):
    param = getattr(request, "param", {})

    console = Mock()
    if not param.get("failure", False):
        console.ask.return_value = "username"
        console.ask_password.return_value = "password"
    else:
        console.ask.side_effect = OSError("No input TTY available")
        console.ask_password.side_effect = OSError("No input TTY available")

    return console


@pytest.fixture()
def session(session: Streamlink, console: Mock):
    user_input = ConsoleUserInputRequester(console)
    session.set_option("user-input-requester", user_input)

    return session


@pytest.fixture()
def testplugin(session: Streamlink):
    return _TestPlugin(session, "http://test.se/")


def test_session(session: Streamlink, console: Mock):
    user_input = session.get_option("user-input-requester")
    assert user_input
    assert user_input.console is console


def test_user_input_not_implemented(session: Streamlink, testplugin: _TestPlugin):
    session.set_option("user-input-requester", None)

    with pytest.raises(FatalPluginError) as cm:
        testplugin.input_ask("test")
    assert str(cm.value) == "This plugin requires user input, however it is not supported on this platform"

    with pytest.raises(FatalPluginError) as cm:
        testplugin.input_ask_password("test")
    assert str(cm.value) == "This plugin requires user input, however it is not supported on this platform"


@pytest.mark.parametrize("console", [{"failure": False}], indirect=True)
def test_user_input_console(console: Mock, testplugin: _TestPlugin):
    assert testplugin.input_ask("username") == "username"
    assert console.ask.call_args_list == [call("username: ")]

    assert testplugin.input_ask_password("password") == "password"
    assert console.ask_password.call_args_list == [call("password: ")]


@pytest.mark.parametrize("console", [{"failure": True}], indirect=True)
def test_user_input_console_no_tty(console: Mock, testplugin: _TestPlugin):
    with pytest.raises(FatalPluginError) as cm:
        testplugin.input_ask("username")
    assert str(cm.value) == "User input error: No input TTY available"

    with pytest.raises(FatalPluginError) as cm:
        testplugin.input_ask_password("username")
    assert str(cm.value) == "User input error: No input TTY available"
