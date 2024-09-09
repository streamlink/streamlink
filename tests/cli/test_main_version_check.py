from unittest.mock import Mock

import pytest

import streamlink_cli.main
from streamlink.logger import capturewarnings
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


@pytest.mark.parametrize(
    ("argv", "latest", "aborted", "exit_code"),
    [
        pytest.param(
            ["--version-check"],
            True,
            True,
            130,
            id="aborted",
        ),
        pytest.param(
            ["--version-check"],
            True,
            False,
            0,
            id="latest",
        ),
        pytest.param(
            ["--version-check"],
            False,
            False,
            1,
            id="outdated",
        ),
        pytest.param(
            ["--auto-version-check=True"],
            True,
            False,
            0,
            id="auto-latest",
        ),
        pytest.param(
            ["--auto-version-check=True"],
            False,
            False,
            0,
            id="auto-outdated",
        ),
    ],
    indirect=["argv"],
)
def test_version_check(monkeypatch: pytest.MonkeyPatch, argv: list, latest: bool, aborted: bool, exit_code: int):
    mock_check_version = Mock(return_value=latest, side_effect=KeyboardInterrupt if aborted else None)
    monkeypatch.setattr("streamlink_cli.main.check_version", mock_check_version)

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == exit_code
    assert mock_check_version.call_count == 1
