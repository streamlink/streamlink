import re
from unittest.mock import Mock

import pytest
import requests_mock as rm

import streamlink_cli.main
from streamlink.logger import capturewarnings
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.session import Streamlink


# TODO: merge duplicate fixtures from related test modules


@pytest.fixture(autouse=True)
def argv(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    argv = getattr(request, "param", [])
    monkeypatch.setattr("sys.argv", ["streamlink", *argv])

    return argv


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch, session: Streamlink):
    monkeypatch.setattr("streamlink_cli.main.CONFIG_FILES", [])
    monkeypatch.setattr("streamlink_cli.main.streamlink", session)
    monkeypatch.setattr("streamlink_cli.main.setup_streamlink", Mock())
    monkeypatch.setattr("streamlink_cli.main.setup_plugins", Mock())
    monkeypatch.setattr("streamlink_cli.main.setup_signals", Mock())
    monkeypatch.setattr("streamlink_cli.argparser.find_default_player", Mock())

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


@pytest.fixture(autouse=True)
def _plugins(session: Streamlink):
    @pluginmatcher(re.compile("http://exists$"))
    class FakePlugin(Plugin):
        def _get_streams(self):  # pragma: no cover
            pass

    session.plugins.update({"plugin": FakePlugin})


@pytest.mark.parametrize(
    ("argv", "exit_code"),
    [
        pytest.param(
            ["--can-handle-url", "http://aborted"],
            130,
            id="aborted",
        ),
        pytest.param(
            ["--can-handle-url", "http://exists"],
            0,
            id="exists",
        ),
        pytest.param(
            ["--can-handle-url", "http://exists-redirect"],
            0,
            id="exists-redirect",
        ),
        pytest.param(
            ["--can-handle-url", "http://missing"],
            1,
            id="missing",
        ),
        pytest.param(
            ["--can-handle-url", "http://missing-redirect"],
            1,
            id="missing-redirect",
        ),
        pytest.param(
            ["--can-handle-url-no-redirect", "http://exists"],
            0,
            id="noredirect-exists",
        ),
        pytest.param(
            ["--can-handle-url-no-redirect", "http://exists-redirect"],
            1,
            id="noredirect-exists-redirect",
        ),
        pytest.param(
            ["--can-handle-url-no-redirect", "http://missing"],
            1,
            id="noredirect-missing",
        ),
        pytest.param(
            ["--can-handle-url-no-redirect", "http://missing-redirect"],
            1,
            id="noredirect-missing-redirect",
        ),
    ],
    indirect=["argv"],
)
def test_can_handle_url(requests_mock: rm.Mocker, session: Streamlink, argv: list, exit_code: int):
    requests_mock.request(rm.ANY, "http://aborted", exc=KeyboardInterrupt)  # type: ignore[arg-type]
    requests_mock.request(rm.ANY, "http://exists", content=b"")
    requests_mock.request(rm.ANY, "http://exists-redirect", status_code=301, headers={"Location": "http://exists"})
    requests_mock.request(rm.ANY, "http://missing-redirect", status_code=301, headers={"Location": "http://missing"})

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == exit_code
