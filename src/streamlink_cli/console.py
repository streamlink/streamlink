import json
import logging
import sys
from getpass import getpass

from streamlink.plugin.plugin import UserInputRequester
from streamlink_cli.utils import JSONEncoder

log = logging.getLogger("streamlink.cli")


class ConsoleUserInputRequester(UserInputRequester):
    """
    Request input from the user on the console using the standard ask/askpass methods
    """
    def __init__(self, console):
        self.console = console

    def ask(self, prompt):
        if sys.stdin.isatty():
            return self.console.ask(prompt.strip() + ": ")
        else:
            raise OSError("no TTY available")

    def ask_password(self, prompt):
        if sys.stdin.isatty():
            return self.console.askpass(prompt.strip() + ": ")
        else:
            raise OSError("no TTY available")


class ConsoleOutput:
    def __init__(self, output, json=False):
        self.json = json
        self.output = output

    def set_output(self, output):
        self.output = output

    @classmethod
    def ask(cls, msg, *args, **kwargs):
        if sys.stdin.isatty():
            formatted = msg.format(*args, **kwargs)
            sys.stderr.write(formatted)

            try:
                answer = input()
            except Exception:
                answer = ""

            return answer.strip()
        else:
            return ""

    @classmethod
    def askpass(cls, msg, *args, **kwargs):
        if sys.stdin.isatty():
            return getpass(msg.format(*args, **kwargs))
        else:
            return ""

    def msg(self, msg, *args, **kwargs):
        formatted = f"{msg.format(*args, **kwargs)}\n"
        self.output.write(formatted)

    def msg_json(self, obj):
        if not self.json:
            return

        if hasattr(obj, "__json__"):
            obj = obj.__json__()

        msg = json.dumps(obj, cls=JSONEncoder,
                         indent=2)
        self.msg("{0}", msg)

        if isinstance(obj, dict) and obj.get("error"):
            sys.exit(1)

    def exit(self, msg, *args, **kwargs):
        formatted = msg.format(*args, **kwargs)

        if self.json:
            obj = dict(error=formatted)
            self.msg_json(obj)
        else:
            self.msg("{0}", f"error: {formatted}")

        sys.exit(1)


__all__ = ["ConsoleOutput"]
