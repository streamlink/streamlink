from __future__ import annotations

import logging
from pathlib import Path

from setuptools import Command
from setuptools.command.build_py import build_py

from build_backend.plugins_json import build, to_json


STREAMLINK_PLUGINS_JSON = Path("streamlink", "plugins", "_plugins.json")


__all__ = ["cmdclass"]


class StreamlinkBuildPyCommand(build_py, Command):
    def _build_plugins_json(self) -> None:
        self.announce("building plugins JSON data", logging.INFO)
        output = Path(self.build_lib) / STREAMLINK_PLUGINS_JSON
        output.parent.mkdir(parents=True, exist_ok=True)
        data = build()
        with output.open("w", encoding="utf-8") as fd:
            to_json(data, fd)

    def build_package_data(self) -> None:
        super().build_package_data()

        self._build_plugins_json()


cmdclass: dict[str, type[Command]] = {
    "build_py": StreamlinkBuildPyCommand,
}
