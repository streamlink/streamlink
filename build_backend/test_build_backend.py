import pytest
from setuptools.command.egg_info import egg_info

from build_backend import _filter_cmd_option_args


@pytest.mark.parametrize(
    ("config_settings", "expected", "options"),
    [
        pytest.param(
            None,
            None,
            egg_info.user_options,
            id="Empty config_settings",
        ),
        pytest.param(
            {"foo": "bar"},
            {"foo": "bar"},
            egg_info.user_options,
            id="No --build-option key",
        ),
        pytest.param(
            {"--build-option": "--egg-base=foo/bar -e baz/qux --tag-build foo -b bar --tag-date --no-date -D"},
            {"--build-option": "--egg-base=foo/bar -e baz/qux --tag-build foo -b bar --tag-date --no-date -D"},
            egg_info.user_options,
            id="All egg_info options",
        ),
        pytest.param(
            {"--build-option": "--foo --bar --baz"},
            {},
            egg_info.user_options,
            id="Options unknown to egg_info",
        ),
        pytest.param(
            {"--build-option": "-p win32 --plat-name win32 --plat-name=win32"},
            {},
            egg_info.user_options,
            id="bdist_wheel --plat-name option",
        ),
    ],
)
def test_filter_cmd_option_args(config_settings: dict, expected: str, options: list):
    _filter_cmd_option_args(config_settings, "--build-option", options)
    assert config_settings == expected
