import sys
from getpass import getpass
from json import dumps
from typing import Any, Dict, List, Optional, TextIO, Union

from streamlink.user_input import UserInputRequester
from streamlink_cli.utils import JSONEncoder


class ConsoleUserInputRequester(UserInputRequester):
    """
    Request input from the user on the console using the standard ask/askpass methods
    """
    def __init__(self, console):
        self.console = console

    def ask(self, prompt: str) -> str:
        if not sys.stdin.isatty():
            raise OSError("no TTY available")
        return self.console.ask(f"{prompt.strip()}: ")

    def ask_password(self, prompt: str) -> str:
        if not sys.stdin.isatty():
            raise OSError("no TTY available")
        return self.console.askpass(f"{prompt.strip()}: ")


class ConsoleOutput:
    def __init__(self, output: TextIO, json: bool = False):
        self.json = json
        self.output = output

    def ask(self, prompt: str) -> Optional[str]:
        if not sys.stdin.isatty():
            return None

        self.output.write(prompt)

        # noinspection PyBroadException
        try:
            return input().strip()
        except Exception:
            return None

    def askpass(self, prompt: str) -> Optional[str]:
        if not sys.stdin.isatty():
            return None

        return getpass(prompt, self.output)

    def msg(self, msg: str) -> None:
        if self.json:
            return
        self.output.write(f"{msg}\n")

    def msg_json(self, *objs: Any, **keywords: Any) -> None:
        if not self.json:
            return

        out: Union[List, Dict]
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

        msg = dumps(out, cls=JSONEncoder, indent=2)
        self.output.write(f"{msg}\n")

        if type(out) is dict and out.get("error"):
            sys.exit(1)

    def exit(self, msg: str) -> None:
        if self.json:
            self.msg_json(error=msg)
        else:
            self.msg(f"error: {msg}")

        sys.exit(1)


__all__ = ["ConsoleOutput", "ConsoleUserInputRequester"]
