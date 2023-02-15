from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

import tests.resources
from streamlink.exceptions import NoPluginError, StreamlinkDeprecationWarning
from streamlink_cli.compat import DeprecatedPath
from streamlink_cli.main import setup_config_args


configdir = Path(tests.resources.__path__[0], "cli", "config")


@pytest.fixture()
def _args(request: pytest.FixtureRequest):
    with patch("streamlink_cli.main.args", Namespace(**getattr(request, "param", {}))):
        yield


@pytest.fixture()
def _config_files(request: pytest.FixtureRequest):
    with patch("streamlink_cli.main.CONFIG_FILES", getattr(request, "param", [])):
        yield


@pytest.fixture()
def setup_args():
    with patch("streamlink_cli.main.setup_args") as mock_setup_args:
        yield mock_setup_args


@pytest.fixture(autouse=True)
def _session():
    def resolve_url(name):
        if name == "noplugin":
            raise NoPluginError()
        return name, Mock(__module__=name), name

    with patch("streamlink_cli.main.streamlink") as mock_session:
        mock_session.resolve_url.side_effect = resolve_url
        yield


# noinspection PyTestParametrized
@pytest.mark.usefixtures("_args", "_config_files")
@pytest.mark.parametrize(("_args", "_config_files", "expected", "deprecations"), [
    pytest.param(
        {
            "config": None,
            "url": None,
        },
        [
            configdir / "primary",
            DeprecatedPath(configdir / "secondary"),
        ],
        [
            configdir / "primary",
        ],
        [],
        id="No URL, default config",
    ),
    pytest.param(
        {
            "config": [
                str(configdir / "non-existent"),
            ],
            "url": None,
        },
        [
            configdir / "primary",
            DeprecatedPath(configdir / "secondary"),
        ],
        [],
        [],
        id="No URL, non-existent custom config",
    ),
    pytest.param(
        {
            "config": None,
            "url": "noplugin",
        },
        [
            configdir / "primary",
            DeprecatedPath(configdir / "secondary"),
        ],
        [
            configdir / "primary",
        ],
        [],
        id="No plugin, default config",
    ),
    pytest.param(
        {
            "config": [
                str(configdir / "non-existent"),
            ],
            "url": "noplugin",
        },
        [
            configdir / "primary",
            DeprecatedPath(configdir / "secondary"),
        ],
        [],
        [],
        id="No plugin, non-existent custom config",
    ),
    pytest.param(
        {
            "config": None,
            "url": "testplugin",
        },
        [
            configdir / "primary",
            DeprecatedPath(configdir / "secondary"),
        ],
        [
            configdir / "primary",
            configdir / "primary.testplugin",
        ],
        [],
        id="Default primary config",
    ),
    pytest.param(
        {
            "config": None,
            "url": "testplugin",
        },
        [
            configdir / "non-existent",
            DeprecatedPath(configdir / "secondary"),
        ],
        [
            configdir / "secondary",
            configdir / "secondary.testplugin",
        ],
        [
            (
                StreamlinkDeprecationWarning,
                "Loaded config from deprecated path, see CLI docs for how to migrate: "
                + f"{configdir / 'secondary'}",
            ),
            (
                StreamlinkDeprecationWarning,
                "Loaded plugin config from deprecated path, see CLI docs for how to migrate: "
                + f"{configdir / 'secondary.testplugin'}",
            ),
        ],
        id="Default secondary config",
    ),
    pytest.param(
        {
            "config": [
                str(configdir / "custom"),
            ],
            "url": "testplugin",
        },
        [
            configdir / "primary",
            DeprecatedPath(configdir / "secondary"),
        ],
        [
            configdir / "custom",
            configdir / "primary.testplugin",
        ],
        [],
        id="Custom config with primary plugin",
    ),
    pytest.param(
        {
            "config": [
                str(configdir / "custom"),
            ],
            "url": "testplugin",
        },
        [
            configdir / "non-existent",
            DeprecatedPath(configdir / "secondary"),
        ],
        [
            configdir / "custom",
            DeprecatedPath(configdir / "secondary.testplugin"),
        ],
        [
            (
                StreamlinkDeprecationWarning,
                "Loaded plugin config from deprecated path, see CLI docs for how to migrate: "
                + f"{configdir / 'secondary.testplugin'}",
            ),
        ],
        id="Custom config with deprecated plugin",
    ),
    pytest.param(
        {
            "config": [
                str(configdir / "non-existent"),
                str(configdir / "primary"),
                str(configdir / "secondary"),
            ],
            "url": "testplugin",
        },
        [
            configdir / "primary",
            DeprecatedPath(configdir / "secondary"),
        ],
        [
            configdir / "secondary",
            configdir / "primary",
            configdir / "primary.testplugin",
        ],
        [],
        id="Multiple custom configs",
    ),
], indirect=["_args", "_config_files"])
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
