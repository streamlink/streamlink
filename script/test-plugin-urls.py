#!/usr/bin/env python

import argparse
import importlib
import logging
import re
import sys
from pathlib import Path
from typing import Iterator, List, Optional, Set, Type

from streamlink import Streamlink
from streamlink.logger import basicConfig


# add root dir to sys path, so the "tests" package can be imported
sys.path.append(str(Path(__file__).parent.parent))


from tests.plugins import PluginCanHandleUrl, TUrlOrNamedUrl  # noqa: 402


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "plugin",
        help="The plugin name",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        choices=["debug", "info", "warning", "error"],
        default="info",
        metavar="LEVEL",
        help="The log level",
    )
    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        metavar="WHEN",
        help="Display errors in red color",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Only print the plugin's test URLs",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        action="append",
        default=[],
        metavar="REGEX",
        help="A regex for ignoring specific URLs. Can be set multiple times",
    )

    return parser.parse_args()


COLOR_RESET = "\033[0m"
COLOR_RED = "\033[0;31m"


class LoggingFormatter(logging.Formatter):
    def __init__(self, color="auto", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color

    def formatMessage(self, record: logging.LogRecord) -> str:
        if record.levelno < logging.ERROR:
            template = ":: {message}"
        elif self.color == "never" or self.color == "auto" and not sys.stdout.isatty():
            template = "!! {message}"
        else:
            template = f"{COLOR_RED}!! {{message}}{COLOR_RESET}"

        return template.format(message=super().formatMessage(record))


class PluginUrlTester:
    def __init__(self) -> None:
        args = parse_arguments()

        self.pluginname: str = args.plugin.lower()

        self.dry_run: bool = args.dry_run

        self.loglevel: str = str(args.loglevel).upper()
        self.logcolor: str = args.color
        self.logger: logging.Logger = self._get_logger()

        self.ignorelist: List[str] = args.ignore or []
        self.urls: Set[str] = set()

    def _get_logger(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        logger.setLevel(self.loglevel)
        handler = logging.StreamHandler(stream=sys.stdout)
        formatter = LoggingFormatter(fmt="{message}", style="{", color=self.logcolor)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        basicConfig(
            stream=sys.stdout,
            # indent output of the StreamlinkLogger
            format=":::: {message}",
            # set the StreamlinkLogger's level to the same level as our logger
            level=self.loglevel,
            capture_warnings=True,
        )

        return logger

    def add_url(self, item: TUrlOrNamedUrl) -> None:
        url: str = item[1] if isinstance(item, tuple) else item
        if not any(re.search(ignore, url) for ignore in self.ignorelist):
            self.urls.add(url)

    def iter_urls(self) -> Iterator[TUrlOrNamedUrl]:
        if not re.match(r"^\w+$", self.pluginname):
            raise ValueError("Missing plugin name")

        try:
            module = importlib.import_module(f"tests.plugins.test_{self.pluginname}")
        except Exception as err:
            raise ImportError(f"Could not load test module of plugin {self.pluginname}: {err}") from err

        PluginCanHandleUrlSubclass: Optional[Type[PluginCanHandleUrl]] = next(
            (
                item
                for item in module.__dict__.values()
                if type(item) is type and item is not PluginCanHandleUrl and issubclass(item, PluginCanHandleUrl)
            ),
            None,
        )
        if not PluginCanHandleUrlSubclass:
            raise RuntimeError("Could not find URL test class inheriting from PluginCanHandleURL")

        yield from PluginCanHandleUrlSubclass.urls_all()

    def run(self) -> int:
        code = 0
        session = Streamlink()
        for url in sorted(self.urls):
            self.logger.info(f"Finding streams for URL: {url}")

            # noinspection PyBroadException
            try:
                pluginname, Pluginclass, resolved_url = session.resolve_url(url)
            except Exception:
                self.logger.error("Error while finding plugin")
                code = 1
                continue

            if pluginname != self.pluginname:
                self.logger.error("URL<->Plugin mismatch")
                code = 1
                continue

            # noinspection PyBroadException
            try:
                plugininst = Pluginclass(session, url)
                streams = plugininst.streams()
            except Exception:
                self.logger.error("Error while fetching streams")
                code = 1
                continue

            if not streams:
                self.logger.error("No streams found")
                code = 1
            else:
                self.logger.info(f"Found streams: {', '.join(streams.keys())}")

        return code

    def main(self) -> int:
        try:
            for item in self.iter_urls():
                self.add_url(item)

            if self.dry_run:
                for url in sorted(self.urls):
                    self.logger.info(url)
                return 0

            return self.run()

        except KeyboardInterrupt:
            return 1
        except Exception as err:
            self.logger.error(str(err))
            return 1


if __name__ == "__main__":
    sys.exit(PluginUrlTester().main())
