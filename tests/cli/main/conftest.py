from unittest.mock import Mock

import pytest

import streamlink_cli.main
from streamlink.logger import capturewarnings
from streamlink.session import Streamlink


@pytest.fixture(autouse=True)
def argv(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    argv = getattr(request, "param", [])
    monkeypatch.setattr("sys.argv", ["streamlink", *argv])

    return argv


@pytest.fixture(autouse=True)
def _atexit_register(monkeypatch: pytest.MonkeyPatch):
    mock_atexit_register = Mock()
    original_main = streamlink_cli.main.main

    # Instead of executing the registered atexit functions in the test's teardown phase,
    # execute them after the main() function call, so it's easier for tests to make assertions about mocked function calls.
    # Otherwise, test scope, fixture dependencies and autouse flags would need to be taken into account.
    def _main():
        # noinspection PyUnreachableCode
        try:
            return original_main()
        finally:
            for call_args in mock_atexit_register.call_args_list:
                call_args.args[0](*call_args.args[1:], **call_args.kwargs)

    monkeypatch.setattr("streamlink_cli.main.main", _main)
    monkeypatch.setattr("streamlink_cli.main._atexit_register", mock_atexit_register)


@pytest.fixture(autouse=True)
def _console_output_stream(monkeypatch: pytest.MonkeyPatch):
    # don't wrap stdout/stderr in CLI integration tests, as we're capturing the output
    monkeypatch.setattr("streamlink_cli.console.stream_wrapper.StreamWrapper._wrap", Mock())
    # don't do any feature checks
    monkeypatch.setattr("streamlink_cli.console.stream.ConsoleOutputStream.__new__", lambda cls, *_, **__: object.__new__(cls))


@pytest.fixture(autouse=True)
def mock_console_output_close(monkeypatch: pytest.MonkeyPatch):
    mock_close = Mock()
    monkeypatch.setattr("streamlink_cli.console.console.ConsoleOutput.close", mock_close)

    return mock_close


@pytest.fixture()
def user_input_requester():
    return Mock(
        ask=Mock(return_value=None),
        ask_password=Mock(return_value=None),
    )


@pytest.fixture(autouse=True)
def session(session: Streamlink, user_input_requester: Mock):
    session.set_option("user-input-requester", user_input_requester)

    return session


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch, requests_mock: Mock, session: Streamlink):
    monkeypatch.setattr("streamlink_cli.main.CONFIG_FILES", [])
    monkeypatch.setattr("streamlink_cli.main.PLUGIN_DIRS", [])
    monkeypatch.setattr("streamlink_cli.main.streamlink", session)
    monkeypatch.setattr("streamlink_cli.main.setup_streamlink", Mock())
    monkeypatch.setattr("streamlink_cli.main.setup_signals", Mock())
    monkeypatch.setattr("streamlink_cli.argparser.find_default_player", Mock(return_value=None))

    level = streamlink_cli.main.logger.root.level

    try:
        yield
    finally:
        capturewarnings(False)
        streamlink_cli.main.logger.root.handlers.clear()
        streamlink_cli.main.logger.root.setLevel(level)
        streamlink_cli.main.args = None  # type: ignore[assignment]
        streamlink_cli.main.console = None  # type: ignore[assignment]


@pytest.fixture(autouse=True)
def _euid(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    euid = getattr(request, "param", 1000)
    monkeypatch.setattr("os.geteuid", Mock(return_value=euid), raising=False)
