from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, call

import pytest

import tests.resources
from streamlink import Streamlink
from streamlink.exceptions import NoPluginError, StreamlinkDeprecationWarning
from streamlink_cli.compat import DeprecatedPath
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
    ("_args", "_config_files", "expected", "deprecations"),
    [
        pytest.param(
            {
                "no_config": False,
                "config": None,
                "url": None,
            },
            [
                CONFIGDIR / "primary",
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [
                CONFIGDIR / "primary",
            ],
            [],
            id="No URL, default config",
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
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [],
            [],
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
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [
                CONFIGDIR / "primary",
            ],
            [],
            id="No plugin, default config",
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
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [],
            [],
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
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [
                CONFIGDIR / "primary",
                CONFIGDIR / "primary.testplugin",
            ],
            [],
            id="Default primary config",
        ),
        pytest.param(
            {
                "no_config": False,
                "config": None,
                "url": "testplugin",
            },
            [
                CONFIGDIR / "non-existent",
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [
                CONFIGDIR / "secondary",
                CONFIGDIR / "secondary.testplugin",
            ],
            [
                (
                    StreamlinkDeprecationWarning,
                    "Loaded config from deprecated path, see CLI docs for how to migrate: "
                    + f"{CONFIGDIR / 'secondary'}",
                ),
                (
                    StreamlinkDeprecationWarning,
                    "Loaded plugin config from deprecated path, see CLI docs for how to migrate: "
                    + f"{CONFIGDIR / 'secondary.testplugin'}",
                ),
            ],
            id="Default secondary config",
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
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [
                CONFIGDIR / "custom",
                CONFIGDIR / "primary.testplugin",
            ],
            [],
            id="Custom config with primary plugin",
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
                CONFIGDIR / "non-existent",
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [
                CONFIGDIR / "custom",
                DeprecatedPath(CONFIGDIR / "secondary.testplugin"),
            ],
            [
                (
                    StreamlinkDeprecationWarning,
                    "Loaded plugin config from deprecated path, see CLI docs for how to migrate: "
                    + f"{CONFIGDIR / 'secondary.testplugin'}",
                ),
            ],
            id="Custom config with deprecated plugin",
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
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [
                CONFIGDIR / "secondary",
                CONFIGDIR / "primary",
                CONFIGDIR / "primary.testplugin",
            ],
            [],
            id="Multiple custom configs",
        ),
        pytest.param(
            {
                "no_config": True,
                "config": [],
                "url": "testplugin",
            },
            [],
            [],
            [],
            id="No config",
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
            [],
            [],
            [],
            id="No config with multiple custom configs",
        ),
        pytest.param(
            {
                "no_config": True,
                "config": [],
                "url": "testplugin",
            },
            [
                CONFIGDIR / "primary",
                DeprecatedPath(CONFIGDIR / "secondary"),
            ],
            [],
            [],
            id="No config with multiple default configs",
        ),
    ],
    indirect=["_args", "_config_files"],
)
def test_setup_config_args(
    recwarn: pytest.WarningsRecorder,
    setup_args: Mock,
    expected: list,
    deprecations: list,
):
    parser = Mock()
    setup_config_args(parser)
    assert setup_args.call_args_list == ([call(parser, expected, ignore_unknown=False)] if expected else []), \
        "Calls setup_args with the correct list of config files"
    assert [(record.category, str(record.message)) for record in recwarn.list] == deprecations, \
        "Raises the correct deprecation warnings"
