from pathlib import Path
from unittest.mock import Mock, call

import pytest

import streamlink_cli.main


@pytest.fixture(autouse=True)
def _run(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("streamlink_cli.main.run", Mock(return_value=0))


@pytest.fixture(autouse=True)
def plugin_dirs(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    plugin_dirs = getattr(request, "param", None)
    monkeypatch.setattr("streamlink_cli.main.PLUGIN_DIRS", plugin_dirs if plugin_dirs is not None else ["DEFAULT"])


@pytest.fixture(autouse=True)
def mock_load_plugins(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    mock_load_plugins = Mock()
    monkeypatch.setattr("streamlink_cli.main.load_plugins", mock_load_plugins)
    return mock_load_plugins


@pytest.mark.parametrize(
    ("argv", "plugin_dirs", "expected"),
    [
        pytest.param(
            [],
            None,
            [
                call(["DEFAULT"], showwarning=False),
            ],
            id="default",
        ),
        pytest.param(
            ["--no-plugin-sideloading"],
            None,
            [],
            id="no-plugin-sideloading",
        ),
        pytest.param(
            ["--plugin-dir=custom1", "--plugin-dir=custom2"],
            None,
            [
                call(["DEFAULT"], showwarning=False),
                call([Path("custom1"), Path("custom2")]),
            ],
            id="custom-paths",
        ),
        pytest.param(
            ["--plugin-dirs=custom1,custom2"],
            None,
            [
                call(["DEFAULT"], showwarning=False),
                call([Path("custom1"), Path("custom2")]),
            ],
            id="custom-paths-deprecated",
        ),
        pytest.param(
            ["--no-plugin-sideloading", "--plugin-dir=custom1", "--plugin-dir=custom2"],
            None,
            [
                call([Path("custom1"), Path("custom2")]),
            ],
            id="custom-paths-without-sideloading",
        ),
    ],
    indirect=["argv", "plugin_dirs"],
)
def test_setup_plugins(argv: list, plugin_dirs: list, mock_load_plugins: Mock, expected: list[str]):
    with pytest.raises(SystemExit):
        streamlink_cli.main.main()

    assert mock_load_plugins.call_args_list == expected
