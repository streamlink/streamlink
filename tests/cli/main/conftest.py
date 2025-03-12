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
    monkeypatch.setattr("streamlink_cli.main.streamlink", session)
    monkeypatch.setattr("streamlink_cli.main.setup_streamlink", Mock())
    monkeypatch.setattr("streamlink_cli.main.setup_plugins", Mock())
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
