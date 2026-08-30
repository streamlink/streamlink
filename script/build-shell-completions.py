#!/usr/bin/env python

from __future__ import annotations

import argparse
import logging
import sys
from importlib.metadata import version
from pathlib import Path

import shtab

# noinspection PyProtectedMember
from streamlink_cli._parser import get_parser as get_streamlink_cli_parser  # ruff: ignore[import-private-name]


SHELLS = {
    "bash": "streamlink",
    "fish": "streamlink.fish",
    "zsh": "_streamlink",
}
OUTPUT_PATH = Path(__file__).parent.parent / "completions"


log = logging.getLogger("build-shell-completions")


def build(args: argparse.Namespace) -> int:
    shells: list[str] = list(args.shell) or list(SHELLS.keys())
    for shell in shells:
        if shell not in SHELLS or shell not in shtab.SUPPORTED_SHELLS:
            raise ValueError(f"Unknown or unsupported shell: {shell}")

    for shell in shells:
        log.info("Building shell completions for %s", shell)
        shell_dir: Path = args.output / shell
        shell_dir.mkdir(parents=True, exist_ok=True)
        shell_file: Path = shell_dir / SHELLS[shell]

        log.info("Initializing new Streamlink CLI parser (%s)", version("streamlink"))
        parser: argparse.ArgumentParser = get_streamlink_cli_parser()
        completion = shtab.complete(
            parser=parser,
            shell=shell,
            root_prefix=None,
            preamble="",
        )

        log.info("Writing shell completion file to %s", shell_file)
        with shell_file.open(mode="w", encoding="utf-8") as fp:
            fp.write(completion)

    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("shell", nargs="*", default=[])
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--verbose", action="store_const", const=logging.DEBUG, default=logging.INFO)

    try:
        args = parser.parse_args(argv[1:])
        logging.basicConfig(level=args.verbose)

        return build(args)

    except Exception as err:
        sys.stderr.write(f"{err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
