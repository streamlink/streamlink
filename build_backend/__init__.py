from __future__ import annotations

import shlex
from typing import Any

from setuptools import build_meta as _build_meta

# re-export everything from `setuptools.build_meta`, so that we don't have to worry about any hooks which we don't override
# https://peps.python.org/pep-0517/
# https://peps.python.org/pep-0660/
# noinspection PyUnresolvedReferences
from setuptools.build_meta import *  # noqa: F403
from setuptools.command.egg_info import egg_info as _egg_info


# ----


def get_requires_for_build_wheel(  # type: ignore[no-redef]
    config_settings: dict | None = None,
) -> list[str]:  # pragma: no cover
    # Streamlink publishes three wheels on PyPI: the generic "any" wheel, the "win32" wheel and the "win-amd64" wheel:
    # The Windows-wheels are special, because they include a "gui_scripts" entry point, which is used by the `pip` frontend
    # to generate the "streamlinkw" launcher, which doesn't open a terminal window when launching it from a GUI application.
    #
    # In order to build these special Windows-wheels, the `--plat-name=...` CLI argument needs to get passed
    # to the `bdist_wheel` setuptools command (provided by the `wheel` package). With the introduction of PEP517 however,
    # setuptools's CLI is not used directly anymore, and instead, we have to build the wheels using the `build` package
    # and the `--wheel --config-setting=--build-option=...` args, which are then forwarded to setuptools via the PEP517 hooks.
    #
    # Since `build==1.0.0` though, the `--config-setting` data now gets passed to all build-backend hooks involved,
    # even `get_requires_for_build_wheel()`. This results in the build failing, as it executes setuptools's `egg_info` command,
    # which doesn't accept the `--plat-name` argument or any other `bdist_wheel` command options.
    #
    # As a consequence of this, we need to override the build-backend and the `get_requires_for_build_wheel()` hook, so that
    # we can filter out arguments which are not relevant to the `egg_info` command.
    _filter_cmd_option_args(
        config_settings,
        "--build-option",
        # types-setuptools-70.3.0.20240710 has the wrong type for
        #   setuptools.command.egg_info.user_options (setuptools._distutils.cmd.Command.user_options)
        _egg_info.user_options,  # type: ignore[arg-type]
    )

    return _build_meta.get_requires_for_build_wheel(config_settings)


# ----


def _filter_cmd_option_args(
    config_settings: dict | None,
    key: str,
    # https://github.com/pypa/setuptools/blob/v71.1.0/setuptools/_distutils/fancy_getopt.py#L47-L54
    # https://github.com/pypa/setuptools/blob/v71.1.0/setuptools/_distutils/fancy_getopt.py#L152-L156
    options: list[tuple[str, str | None, str] | tuple[str, str | None, str, Any]],
) -> None:
    """Filter out args which are not recognized by a specific command and its options"""

    if not config_settings or not config_settings.get(key):
        return

    parsed = shlex.split(config_settings[key])

    result = []
    val_next = False
    for item in parsed:
        if val_next:
            val_next = False
            result.append(item)
            continue
        full: str
        shorthand: str | None
        for full, shorthand, *_ in options:
            is_boolean = full[-1] != "="
            is_shorthand = shorthand is not None and item == f"-{shorthand}"
            if not is_boolean and (is_shorthand or item == f"--{full[:-1]}"):
                val_next = True
                result.append(item)
                break
            if (
                is_boolean and (is_shorthand or item == f"--{full}")
                or not is_boolean and item.startswith(f"--{full}")
            ):  # fmt: skip
                result.append(item)
                break

    if result:
        config_settings[key] = shlex.join(result)
    else:
        del config_settings[key]
