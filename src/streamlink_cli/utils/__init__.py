import json
from contextlib import contextmanager

from streamlink_cli.utils.http_server import HTTPServer
from streamlink_cli.utils.player import find_default_player
from streamlink_cli.utils.progress import progress
from streamlink_cli.utils.stream import stream_to_url

__all__ = [
    "HTTPServer", "JSONEncoder",
    "find_default_player", "ignored", "progress", "stream_to_url"
]


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__json__"):
            return obj.__json__()
        elif isinstance(obj, bytes):
            return obj.decode("utf8", "ignore")
        else:
            return json.JSONEncoder.default(self, obj)


@contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass
