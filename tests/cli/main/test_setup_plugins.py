from pathlib import Path
from unittest.mock import Mock, call

import pytest

import streamlink_cli.main
from streamlink import Streamlink


@pytest.fixture(autouse=True)
def _cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    Path(tmp_path, "DEFAULT").mkdir()
    Path(tmp_path, "custom1").mkdir()


@pytest.fixture(autouse=True)
def _run(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("streamlink_cli.main.run", Mock(return_value=0))


@pytest.fixture()
def plugin_dirs(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    value = getattr(request, "param", None)
    plugin_dirs = value if value is not None else [Path("DEFAULT"), Path("DOESNOTEXIST")]
    monkeypatch.setattr("streamlink_cli.main.PLUGIN_DIRS", plugin_dirs)


@pytest.fixture()
def mock_load_path(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, session: Streamlink):
    mock_load_path = Mock()
    monkeypatch.setattr(session.plugins, "load_path", mock_load_path)
    return mock_load_path


@pytest.mark.parametrize(
    ("argv", "plugin_dirs", "expected", "log"),
    [
        pytest.param(
            [],
            None,
            [
                call(Path("DEFAULT")),
            ],
            [],
            id="default",
        ),
        pytest.param(
            ["--no-plugin-sideloading"],
            None,
            [],
            [],
            id="no-plugin-sideloading",
        ),
        pytest.param(
            ["--plugin-dir=custom1", "--plugin-dir=custom2"],
            None,
            [
                call(Path("DEFAULT")),
                call(Path("custom1")),
            ],
            [
                ("cli", "warning", "Plugin path custom2 does not exist or is not a directory!"),
            ],
            id="custom-paths",
        ),
        pytest.param(
            ["--plugin-dirs=custom1,custom2"],
            None,
            [
                call(Path("DEFAULT")),
                call(Path("custom1")),
            ],
            [
                ("cli", "warning", "Plugin path custom2 does not exist or is not a directory!"),
            ],
            id="custom-paths-deprecated",
        ),
        pytest.param(
            ["--no-plugin-sideloading", "--plugin-dir=custom1", "--plugin-dir=custom2"],
            None,
            [
                call(Path("custom1")),
            ],
            [
                ("cli", "warning", "Plugin path custom2 does not exist or is not a directory!"),
            ],
            id="custom-paths-without-sideloading",
        ),
    ],
    indirect=["argv", "plugin_dirs"],
)
def test_setup_plugins(
    caplog: pytest.LogCaptureFixture,
    argv: list,
    plugin_dirs: list,
    mock_load_path: Mock,
    expected: list[str],
    log: list,
):
    caplog.set_level(1, "streamlink")

    with pytest.raises(SystemExit):
        streamlink_cli.main.main()

    assert mock_load_path.call_args_list == expected
    assert [(record.name, record.levelname, record.message) for record in caplog.records] == log
