from __future__ import annotations

import sys
from contextlib import contextmanager
from getpass import getpass
from json import dumps
from typing import Any, TextIO

from streamlink.user_input import UserInputRequester
from streamlink_cli.utils import JSONEncoder


class ConsoleUserInputRequester(UserInputRequester):
    """
    Request input from the user on the console using the standard ask/askpass methods
    """

    def __init__(self, console: ConsoleOutput):
        self.console = console

    def ask(self, prompt: str) -> str:
        return self.console.ask(f"{prompt.strip()}: ")

    def ask_password(self, prompt: str) -> str:
        return self.console.ask_password(f"{prompt.strip()}: ")


class ConsoleOutput:
    def __init__(self, output: TextIO, json: bool = False):
        self.json = json
        self.output = output

    @contextmanager
    def _prompt(self):
        if not sys.stdin or not sys.stdin.isatty():
            raise OSError("No input TTY available")
        if not self.output or not self.output.isatty():
            raise OSError("No output TTY available")

        try:
            yield
        except OSError:
            raise
        except Exception as err:
            raise OSError(err) from err

    def ask(self, prompt: str) -> str:
        with self._prompt():
            self.output.write(prompt)
            return input().strip()

    def ask_password(self, prompt: str) -> str:
        with self._prompt():
            return getpass(prompt=prompt, stream=self.output)

    def msg(self, msg: str) -> None:
        if self.json:
            return
        self.output.write(f"{msg}\n")

    def msg_json(self, *objs: Any, **keywords: Any) -> None:
        if not self.json:
            return

        out: list | dict
        if objs and isinstance(objs[0], list):
            out = []
            for obj in objs:
                if isinstance(obj, list):
                    out.extend(obj)
                else:
                    if hasattr(obj, "__json__") and callable(obj.__json__):
                        obj = obj.__json__()
                    out.append(obj)
            if keywords:
                out.append(keywords)
        else:
            out = {}
            for obj in objs:
                if hasattr(obj, "__json__") and callable(obj.__json__):
                    obj = obj.__json__()
                if not isinstance(obj, dict):
                    continue
                out.update(**obj)
            out.update(**keywords)

        # don't escape Unicode characters outside the ASCII range if the output encoding is UTF-8
        ensure_ascii = self.output.encoding != "utf-8"

        msg = dumps(out, cls=JSONEncoder, ensure_ascii=ensure_ascii, indent=2)
        self.output.write(f"{msg}\n")


__all__ = ["ConsoleOutput", "ConsoleUserInputRequester"]
