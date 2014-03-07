import hashlib
import hmac
import json
import re
import zlib

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import requests

from .compat import urljoin, urlparse, parse_qsl
from .exceptions import PluginError

SWF_KEY = b"Genuine Adobe Flash Player 001"


def urlget(url, *args, **kwargs):
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

# Keep compatiblity
urlopen = urlget


def urlresolve(url):
    res = urlget(url, stream=True, allow_redirects=False)

    if res.status_code == 302 and "location" in res.headers:
        return res.headers["location"]
    else:
        return url


def swfdecompress(data):
    if data[:3] == b"CWS":
        data = b"F" + data[1:8] + zlib.decompress(data[8:])

    return data


def swfverify(url):
    res = urlopen(url)
    swf = swfdecompress(res.content)

    h = hmac.new(SWF_KEY, swf, hashlib.sha256)

    return h.hexdigest(), len(swf)


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


def parse_json(data, jsontype="JSON", exception=PluginError):
    try:
        jsondata = json.loads(data)
    except ValueError as err:
        if len(data) > 35:
            snippet = data[:35] + "..."
        else:
            snippet = data

        raise exception("Unable to parse {0}: {1} ({2})".format(jsontype, err,
                                                                snippet))

    return jsondata


def res_json(res, jsontype="JSON", exception=PluginError):
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


def parse_xml(data, xmltype="XML", ignore_ns=False, exception=PluginError):
    if ignore_ns:
        data = re.sub(" xmlns=\"(.+?)\"", "", data)

    try:
        tree = ET.fromstring(data)
    except Exception as err:
        if len(data) > 35:
            snippet = data[:35] + "..."
        else:
            snippet = data

        raise exception("Unable to parse {0}: {1} ({2})".format(xmltype, err,
                                                                snippet))

    return tree


def parse_qsd(*args, **kwargs):
    return dict(parse_qsl(*args, **kwargs))


def res_xml(res, *args, **kw):
    return parse_xml(res.text, *args, **kw)


def rtmpparse(url):
    parse = urlparse(url)
    netloc = "{hostname}:{port}".format(hostname=parse.hostname,
                                        port=parse.port or 1935)
    split = parse.path.split("/")
    app = "/".join(split[1:2])

    if len(split) > 2:
        playpath = "/".join(split[2:])

        if len(parse.query) > 0:
            playpath += "?" + parse.query
    else:
        playpath = ""

    tcurl = "{scheme}://{netloc}/{app}".format(scheme=parse.scheme,
                                               netloc=netloc,
                                               app=app)

    return (tcurl, playpath)


__all__ = ["urlopen", "urlget", "urlresolve", "swfdecompress", "swfverify",
           "verifyjson", "absolute_url", "parse_qsd", "parse_json", "res_json",
           "parse_xml", "res_xml", "rtmpparse", "prepend_www"]
