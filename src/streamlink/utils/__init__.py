import functools
import json
import re
import zlib

try:
    import xml.etree.cElementTree as ET
except ImportError:  # pragma: no cover
    import xml.etree.ElementTree as ET

from streamlink.compat import urljoin, urlparse, parse_qsl, is_py2, urlunparse, is_py3
from streamlink.exceptions import PluginError
from streamlink.utils.named_pipe import NamedPipe


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
        data = re.sub(br" xmlns=\"(.+?)\"", b"", data)

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


def update_scheme(current, target):
    """
    Take the scheme from the current URL and applies it to the
    target URL if the target URL startswith // or is missing a scheme
    :param current: current URL
    :param target: target URL
    :return: target URL with the current URLs scheme
    """
    target_p = urlparse(target)
    if not target_p.scheme and target_p.netloc:
        return "{0}:{1}".format(urlparse(current).scheme,
                                urlunparse(target_p))
    elif not target_p.scheme and not target_p.netloc:
        return "{0}://{1}".format(urlparse(current).scheme,
                                  urlunparse(target_p))
    else:
        return target


def url_equal(first, second, ignore_scheme=False, ignore_netloc=False, ignore_path=False, ignore_params=False,
              ignore_query=False, ignore_fragment=False):
    """
    Compare two URLs and return True if they are equal, some parts of the URLs can be ignored
    :param first: URL
    :param second: URL
    :param ignore_scheme: ignore the scheme
    :param ignore_netloc: ignore the netloc
    :param ignore_path: ignore the path
    :param ignore_params: ignore the params
    :param ignore_query: ignore the query string
    :param ignore_fragment: ignore the fragment
    :return: result of comparison
    """
    # <scheme>://<netloc>/<path>;<params>?<query>#<fragment>

    firstp = urlparse(first)
    secondp = urlparse(second)

    return ((firstp.scheme == secondp.scheme or ignore_scheme) and
            (firstp.netloc == secondp.netloc or ignore_netloc) and
            (firstp.path == secondp.path or ignore_path) and
            (firstp.params == secondp.params or ignore_params) and
            (firstp.query == secondp.query or ignore_query) and
            (firstp.fragment == secondp.fragment or ignore_fragment))


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


#####################################
# Deprecated functions, do not use. #
#####################################

import requests


def urlget(url, *args, **kwargs):  # pragma: no cover
    """This function is deprecated."""
    data = kwargs.pop("data", None)
    exception = kwargs.pop("exception", PluginError)
    method = kwargs.pop("method", "GET")
    session = kwargs.pop("session", None)
    timeout = kwargs.pop("timeout", 20)

    if data is not None:
        method = "POST"

    try:
        if session:
            res = session.request(method, url, timeout=timeout, data=data,
                                  *args, **kwargs)
        else:
            res = requests.request(method, url, timeout=timeout, data=data,
                                   *args, **kwargs)

        res.raise_for_status()
    except (requests.exceptions.RequestException, IOError) as rerr:
        err = exception("Unable to open URL: {url} ({err})".format(url=url,
                                                                   err=rerr))
        err.err = rerr
        raise err

    return res


urlopen = urlget


def urlresolve(url):  # pragma: no cover
    """This function is deprecated."""
    res = urlget(url, stream=True, allow_redirects=False)

    if res.status_code == 302 and "location" in res.headers:
        return res.headers["location"]
    else:
        return url


def res_xml(res, *args, **kw):  # pragma: no cover
    """This function is deprecated."""
    return parse_xml(res.text, *args, **kw)


def res_json(res, jsontype="JSON", exception=PluginError):  # pragma: no cover
    """This function is deprecated."""
    try:
        jsondata = res.json()
    except ValueError as err:
        if len(res.text) > 35:
            snippet = res.text[:35] + "..."
        else:
            snippet = res.text

        raise exception("Unable to parse {0}: {1} ({2})".format(jsontype, err,
                                                                snippet))

    return jsondata


import hmac
import hashlib

SWF_KEY = b"Genuine Adobe Flash Player 001"


def swfverify(url):  # pragma: no cover
    """This function is deprecated."""
    res = urlopen(url)
    swf = swfdecompress(res.content)

    h = hmac.new(SWF_KEY, swf, hashlib.sha256)

    return h.hexdigest(), len(swf)


def escape_librtmp(value):
    if isinstance(value, bool):
        value = "1" if value else "0"
    if isinstance(value, int):
        value = str(value)

    # librtmp expects some characters to be escaped
    value = value.replace("\\", "\\5c")
    value = value.replace(" ", "\\20")
    value = value.replace('"', "\\22")
    return value


__all__ = ["urlopen", "urlget", "urlresolve", "swfdecompress", "swfverify",
           "verifyjson", "absolute_url", "parse_qsd", "parse_json", "res_json",
           "parse_xml", "res_xml", "rtmpparse", "prepend_www", "NamedPipe",
           "escape_librtmp"]
