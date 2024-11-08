from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, call

import pytest

import tests.resources
from streamlink import Streamlink
from streamlink.exceptions import NoPluginError
from streamlink_cli.main import setup_config_args


CONFIGDIR = Path(tests.resources.__path__[0], "cli", "config")


@pytest.fixture()
def _args(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("streamlink_cli.main.args", Namespace(**getattr(request, "param", {})))


@pytest.fixture()
def _config_files(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("streamlink_cli.main.CONFIG_FILES", getattr(request, "param", []))


@pytest.fixture()
def setup_args(monkeypatch: pytest.MonkeyPatch):
    mock_setup_args = Mock()
    monkeypatch.setattr("streamlink_cli.main.setup_args", mock_setup_args)

    return mock_setup_args


@pytest.fixture()
def session(monkeypatch: pytest.MonkeyPatch, session: Streamlink):
    def resolve_url(name):
        if name == "noplugin":
            raise NoPluginError()
        return name, Mock(__module__=name), name

    monkeypatch.setattr(session, "resolve_url", resolve_url)

    return session


# noinspection PyTestParametrized
@pytest.mark.usefixtures("_args", "_config_files")
@pytest.mark.parametrize(
    ("_args", "_config_files", "expected"),
    [
        pytest.param(
            {
                "no_config": False,
                "config": None,
                "url": None,
            },
            [
                CONFIGDIR / "primary",
            ],
            [
                CONFIGDIR / "primary",
            ],
            id="No URL, default config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": [
                    str(CONFIGDIR / "custom"),
                ],
                "url": None,
            },
            [
                CONFIGDIR / "primary",
            ],
            [
                CONFIGDIR / "custom",
            ],
            id="No URL, custom config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": [],
                "url": None,
            },
            [
                CONFIGDIR / "non-existent",
            ],
            None,
            id="No URL, non-existent default config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": [
                    str(CONFIGDIR / "non-existent"),
                ],
                "url": None,
            },
            [
                CONFIGDIR / "primary",
            ],
            None,
            id="No URL, non-existent custom config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": None,
                "url": "noplugin",
            },
            [
                CONFIGDIR / "primary",
            ],
            [
                CONFIGDIR / "primary",
            ],
            id="No plugin, default config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": [
                    str(CONFIGDIR / "custom"),
                ],
                "url": "noplugin",
            },
            [
                CONFIGDIR / "primary",
            ],
            [
                CONFIGDIR / "custom",
            ],
            id="No plugin, custom config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": [],
                "url": "noplugin",
            },
            [
                CONFIGDIR / "non-existent",
            ],
            None,
            id="No plugin, non-existent default config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": [
                    str(CONFIGDIR / "non-existent"),
                ],
                "url": "noplugin",
            },
            [
                CONFIGDIR / "primary",
            ],
            None,
            id="No plugin, non-existent custom config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": None,
                "url": "testplugin",
            },
            [
                CONFIGDIR / "primary",
            ],
            [
                CONFIGDIR / "primary",
                CONFIGDIR / "primary.testplugin",
            ],
            id="Testplugin, default config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": None,
                "url": "testplugin",
            },
            [
                CONFIGDIR / "non-existent",
            ],
            None,
            id="Testplugin, non-existent default config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": [
                    str(CONFIGDIR / "custom"),
                ],
                "url": "testplugin",
            },
            [
                CONFIGDIR / "primary",
            ],
            [
                CONFIGDIR / "custom",
                CONFIGDIR / "primary.testplugin",
            ],
            id="Testplugin, custom config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": [
                    str(CONFIGDIR / "non-existent"),
                ],
                "url": "testplugin",
            },
            [
                CONFIGDIR / "primary",
            ],
            [
                CONFIGDIR / "primary.testplugin",
            ],
            id="Testplugin, non-existent custom config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": [
                    str(CONFIGDIR / "non-existent"),
                    str(CONFIGDIR / "primary"),
                    str(CONFIGDIR / "secondary"),
                ],
                "url": "testplugin",
            },
            [
                CONFIGDIR / "primary",
            ],
            [
                CONFIGDIR / "secondary",
                CONFIGDIR / "primary",
                CONFIGDIR / "primary.testplugin",
            ],
            id="Testplugin, multiple custom configs",
        ),
        pytest.param(
            {
                "no_config": True,
                "config": [],
                "url": "testplugin",
            },
            [
                CONFIGDIR / "primary",
            ],
            None,
            id="No config, default config",
        ),
        pytest.param(
            {
                "no_config": True,
                "config": [
                    str(CONFIGDIR / "primary"),
                    str(CONFIGDIR / "secondary"),
                ],
                "url": "testplugin",
            },
            [
                CONFIGDIR / "primary",
            ],
            None,
            id="No config, multiple custom configs",
        ),
    ],
    indirect=["_args", "_config_files"],
)
@pytest.mark.parametrize("ignore_unknown", [True, False])
def test_setup_config_args(
    recwarn: pytest.WarningsRecorder,
    setup_args: Mock,
    expected: list | None,
    ignore_unknown: bool,
):
    parser = Mock()
    setup_config_args(parser, ignore_unknown=ignore_unknown)
    if expected is not None:
        assert setup_args.call_args_list == [call(parser, expected, ignore_unknown=ignore_unknown)]
    else:
        assert setup_args.call_args_list == []
