import zlib
from collections import OrderedDict
from importlib.machinery import FileFinder, SOURCE_SUFFIXES, SourceFileLoader
from importlib.util import module_from_spec
from typing import Dict, Generic, Optional, TypeVar
from urllib.parse import urljoin, urlparse

from streamlink.exceptions import PluginError
from streamlink.utils.lazy_formatter import LazyFormatter
from streamlink.utils.named_pipe import NamedPipe
from streamlink.utils.parse import parse_html, parse_json, parse_qsd, parse_xml
from streamlink.utils.url import update_scheme, url_equal


_loader_details = [(SourceFileLoader, SOURCE_SUFFIXES)]


def load_module(name, path=None):
    finder = FileFinder(path, *_loader_details)
    spec = finder.find_spec(name)
    if not spec or not spec.loader:
        raise ImportError(f"no module named {name}")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def swfdecompress(data):
    if data[:3] == b"CWS":
        data = b"F" + data[1:8] + zlib.decompress(data[8:])

    return data


def verifyjson(json, key):
    if not isinstance(json, dict):
        raise PluginError("JSON result is not a dict")

    if key not in json:
        raise PluginError("Missing '{0}' key in JSON".format(key))

    return json[key]


def absolute_url(baseurl, url):
    if not url.startswith("http"):
        return urljoin(baseurl, url)
    else:
        return url


def prepend_www(url):
    """Changes google.com to www.google.com"""
    parsed = urlparse(url)
    if parsed.netloc.split(".")[0] != "www":
        return parsed.scheme + "://www." + parsed.netloc + parsed.path
    else:
        return url


def rtmpparse(url):
    parse = urlparse(url)
    netloc = "{hostname}:{port}".format(hostname=parse.hostname,
                                        port=parse.port or 1935)
    split = list(filter(None, parse.path.split("/")))
    playpath = None
    if len(split) > 2:
        app = "/".join(split[:2])
        playpath = "/".join(split[2:])
    elif len(split) == 2:
        app, playpath = split
    else:
        app = split[0]

    if len(parse.query) > 0:
        playpath += "?{parse.query}".format(parse=parse)

    tcurl = "{scheme}://{netloc}/{app}".format(scheme=parse.scheme,
                                               netloc=netloc,
                                               app=app)

    return tcurl, playpath


def search_dict(data, key):
    """
    Search for a key in a nested dict, or list of nested dicts, and return the values.

    :param data: dict/list to search
    :param key: key to find
    :return: matches for key
    """
    if isinstance(data, dict):
        for dkey, value in data.items():
            if dkey == key:
                yield value
            yield from search_dict(value, key)
    elif isinstance(data, list):
        for value in data:
            yield from search_dict(value, key)


def escape_librtmp(value):  # pragma: no cover
    if isinstance(value, bool):
        value = "1" if value else "0"
    if isinstance(value, int):
        value = str(value)

    # librtmp expects some characters to be escaped
    value = value.replace("\\", "\\5c")
    value = value.replace(" ", "\\20")
    value = value.replace('"', "\\22")
    return value


TCacheKey = TypeVar("TCacheKey")
TCacheValue = TypeVar("TCacheValue")


class LRUCache(Generic[TCacheKey, TCacheValue]):
    def __init__(self, num: int):
        # TODO: fix type after dropping py36
        self.cache: Dict[TCacheKey, TCacheValue] = OrderedDict()
        self.num = num

    def get(self, key: TCacheKey) -> Optional[TCacheValue]:
        if key not in self.cache:
            return None
        # noinspection PyUnresolvedReferences
        self.cache.move_to_end(key)
        return self.cache[key]

    def set(self, key: TCacheKey, value: TCacheValue) -> None:
        self.cache[key] = value
        # noinspection PyUnresolvedReferences
        self.cache.move_to_end(key)
        if len(self.cache) > self.num:
            # noinspection PyArgumentList
            self.cache.popitem(last=False)


__all__ = [
    "load_module",
    "escape_librtmp", "rtmpparse", "swfdecompress",
    "verifyjson",
    "absolute_url", "prepend_www",
    "search_dict",
    "LRUCache",
    "LazyFormatter",
    "NamedPipe",
    "parse_html", "parse_json", "parse_qsd", "parse_xml",
    "update_scheme", "url_equal",
]
