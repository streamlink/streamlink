import json
import sys
import logging
from getpass import getpass

from .compat import input
from .utils import JSONEncoder

log = logging.getLogger("streamlink.cli")


class ConsoleOutput(object):
    def __init__(self, output, streamlink, json=False):
        self.streamlink = streamlink

        self.json = json
        self.set_output(output)

    def set_level(self, level):
        self.streamlink.set_loglevel(level)

    def set_output(self, output):
        self.output = output

    def ask(self, msg, *args, **kwargs):
        formatted = msg.format(*args, **kwargs)
        sys.stderr.write(formatted)

        try:
            answer = input()
        except Exception:
            answer = ""

        return answer.strip()

    def askpass(self, msg, *args, **kwargs):
        formatted = msg.format(*args, **kwargs)

        return getpass(formatted)

    def msg(self, msg, *args, **kwargs):
        formatted = msg.format(*args, **kwargs)
        formatted = u"{0}\n".format(formatted)

        self.output.write(formatted)

    def msg_json(self, obj):
        if not self.json:
            return

        if hasattr(obj, "__json__"):
            obj = obj.__json__()

        msg = json.dumps(obj, cls=JSONEncoder,
                         indent=2)
        self.msg(u"{0}", msg)

        if isinstance(obj, dict) and obj.get("error"):
            sys.exit(1)

    def exit(self, msg, *args, **kwargs):
        formatted = msg.format(*args, **kwargs)

        if self.json:
            obj = dict(error=formatted)
            self.msg_json(obj)
        else:
            msg = u"error: {0}".format(formatted)
            self.msg(u"{0}", msg)

        sys.exit(1)


__all__ = ["ConsoleOutput"]
