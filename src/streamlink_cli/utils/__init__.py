import json
from datetime import datetime as _datetime

from streamlink_cli.utils.formatter import Formatter
from streamlink_cli.utils.http_server import HTTPServer
from streamlink_cli.utils.player import find_default_player


__all__ = [
    "Formatter", "HTTPServer", "JSONEncoder",
    "datetime",
    "find_default_player",
]


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__json__"):
            return obj.__json__()
        elif isinstance(obj, bytes):
            return obj.decode("utf8", "ignore")
        else:
            return json.JSONEncoder.default(self, obj)


# noinspection PyPep8Naming
class datetime(_datetime):
    def __str__(self):
        return self.strftime("%Y-%m-%d_%H-%M-%S")
