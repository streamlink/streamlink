import json
from sys import getfilesystemencoding

from contextlib import contextmanager

from .http_server import HTTPServer
from streamlink.utils.named_pipe import NamedPipe
from .progress import progress
from .player import find_default_player
from .stream import stream_to_url
from .lazy_formatter import *


__all__ = [
    "NamedPipe", "HTTPServer", "JSONEncoder", "LazyFormatter",
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


def get_filesystem_encoding():
    fileSystemEncoding = getfilesystemencoding()
    if fileSystemEncoding is None: #`None` not possible after python 3.2
        if is_win32:
            fileSystemEncoding = 'mbcs'
        else:
            fileSystemEncoding = 'utf-8'
    return fileSystemEncoding
