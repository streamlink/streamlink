# ruff: noqa: RUF067

import json
from datetime import datetime as _datetime

from streamlink_cli.utils.formatter import Formatter
from streamlink_cli.utils.player import find_default_player


__all__ = [
    "Formatter",
    "JSONEncoder",
    "datetime",
    "find_default_player",
]


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "__json__"):
            return o.__json__()
        elif isinstance(o, bytes):
            return o.decode("utf8", "ignore")
        else:
            return json.JSONEncoder.default(self, o)


# noinspection PyPep8Naming
class datetime(_datetime):
    def __str__(self):
        return self.strftime("%Y-%m-%d_%H-%M-%S")
