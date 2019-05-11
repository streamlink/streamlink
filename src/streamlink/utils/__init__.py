import functools
import json
import re
import xml.etree.ElementTree as ET
import zlib

from streamlink.compat import urljoin, urlparse, parse_qsl, is_py2, is_py3
from streamlink.exceptions import PluginError
from streamlink.utils.named_pipe import NamedPipe
from streamlink.utils.lazy_formatter import LazyFormatter
from streamlink.utils.encoding import get_filesystem_encoding, maybe_decode, maybe_encode
from streamlink.utils.url import update_scheme, url_equal


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


def parse_json(data, name="JSON", exception=PluginError, schema=None):
    """Wrapper around json.loads.

    Wraps errors in custom exception with a snippet of the data in the message.
    """
    try:
        json_data = json.loads(data)
    except ValueError as err:
        snippet = repr(data)
        if len(snippet) > 35:
            snippet = snippet[:35] + " ..."
        else:
            snippet = data

        raise exception("Unable to parse {0}: {1} ({2})".format(name, err, snippet))

    if schema:
        json_data = schema.validate(json_data, name=name, exception=exception)

    return json_data


def parse_xml(data, name="XML", ignore_ns=False, exception=PluginError, schema=None, invalid_char_entities=False):
    """Wrapper around ElementTree.fromstring with some extras.

    Provides these extra features:
     - Handles incorrectly encoded XML
     - Allows stripping namespace information
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    if is_py2 and isinstance(data, unicode):
        data = data.encode("utf8")
    elif is_py3 and isinstance(data, str):
        data = bytearray(data, "utf8")

    if ignore_ns:
        data = re.sub(br"[\t ]xmlns=\"(.+?)\"", b"", data)

    if invalid_char_entities:
        data = re.sub(br'&(?!(?:#(?:[0-9]+|[Xx][0-9A-Fa-f]+)|[A-Za-z0-9]+);)', b'&amp;', data)

    try:
        tree = ET.fromstring(data)
    except Exception as err:
        snippet = repr(data)
        if len(snippet) > 35:
            snippet = snippet[:35] + " ..."

        raise exception("Unable to parse {0}: {1} ({2})".format(name, err, snippet))

    if schema:
        tree = schema.validate(tree, name=name, exception=exception)

    return tree


def parse_qsd(data, name="query string", exception=PluginError, schema=None, **params):
    """Parses a query string into a dict.

    Unlike parse_qs and parse_qsl, duplicate keys are not preserved in
    favor of a simpler return value.
    """

    value = dict(parse_qsl(data, **params))
    if schema:
        value = schema.validate(value, name=name, exception=exception)

    return value


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


def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer


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
            for result in search_dict(value, key):
                yield result
    elif isinstance(data, list):
        for value in data:
            for result in search_dict(value, key):
                yield result


def load_module(name, path=None):
    if is_py3:
        import importlib.machinery
        import importlib.util
        import sys

        loader_details = [(importlib.machinery.SourceFileLoader, importlib.machinery.SOURCE_SUFFIXES)]
        finder = importlib.machinery.FileFinder(path, *loader_details)
        spec = finder.find_spec(name)
        if not spec or not spec.loader:
            raise ImportError("no module named {0}".format(name))
        if sys.version_info[1] > 4:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        else:
            return spec.loader.load_module(name)

    else:
        import imp
        fd, filename, desc = imp.find_module(name, path and [path])
        try:
            return imp.load_module(name, fd, filename, desc)
        finally:
            if fd:
                fd.close()


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


__all__ = ["swfdecompress", "update_scheme", "url_equal",
           "verifyjson", "absolute_url", "parse_qsd", "parse_json",
           "parse_xml", "rtmpparse", "prepend_www", "NamedPipe",
           "escape_librtmp", "LazyFormatter", "get_filesystem_encoding",
           "maybe_decode", "maybe_encode"]
