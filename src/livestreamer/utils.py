import json
import re
import zlib

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from .compat import urljoin, urlparse, parse_qsl, is_py2
from .exceptions import PluginError


def swfdecompress(data):
    if data[:3] == b"CWS":
        data = b"F" + data[1:8] + zlib.decompress(data[8:])

    return data


def verifyjson(json, key):
    if not isinstance(json, dict):
        raise PluginError("JSON result is not a dict")

    if not key in json:
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


def parse_xml(data, name="XML", ignore_ns=False, exception=PluginError, schema=None):
    """Wrapper around ElementTree.fromstring with some extras.

    Provides these extra features:
     - Handles incorrectly encoded XML
     - Allows stripping namespace information
     - Wraps errors in custom exception with a snippet of the data in the message
    """
    if is_py2 and isinstance(data, unicode):
        data = data.encode("utf8")

    if ignore_ns:
        data = re.sub(" xmlns=\"(.+?)\"", "", data)

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

    return (tcurl, playpath)


#####################################
# Deprecated functions, do not use. #
#####################################

import requests

def urlget(url, *args, **kwargs):
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


def urlresolve(url):
    """This function is deprecated."""
    res = urlget(url, stream=True, allow_redirects=False)

    if res.status_code == 302 and "location" in res.headers:
        return res.headers["location"]
    else:
        return url


def res_xml(res, *args, **kw):
    """This function is deprecated."""
    return parse_xml(res.text, *args, **kw)


def res_json(res, jsontype="JSON", exception=PluginError):
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

def swfverify(url):
    """This function is deprecated."""
    res = urlopen(url)
    swf = swfdecompress(res.content)

    h = hmac.new(SWF_KEY, swf, hashlib.sha256)

    return h.hexdigest(), len(swf)


__all__ = ["urlopen", "urlget", "urlresolve", "swfdecompress", "swfverify",
           "verifyjson", "absolute_url", "parse_qsd", "parse_json", "res_json",
           "parse_xml", "res_xml", "rtmpparse", "prepend_www"]
