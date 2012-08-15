from .compat import urllib
from .plugins import PluginError

import hmac, hashlib, zlib, argparse

SWF_KEY = b"Genuine Adobe Flash Player 001"

class ArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, line):
        if line[0] == "#":
            return

        split = line.find("=")
        if split > 0:
            key = line[:split].strip()
            val = line[split+1:].strip()
            yield "--%s=%s" % (key, val)
        else:
            yield "--%s" % line

def urlopen(url, data=None, timeout=None, opener=None):
    try:
        if opener is not None:
            fd = opener.open(url, data, timeout)
        else:
            fd = urllib.urlopen(url, data, timeout)

    except IOError as err:
        if type(err) is urllib.URLError:
            raise PluginError(err.reason)
        else:
            raise PluginError(err)

    return fd

def urlget(url, data=None, timeout=15, opener=None):
    fd = urlopen(url, data, timeout, opener)

    try:
        data = fd.read()
        fd.close()
    except IOError as err:
        if type(err) is urllib.URLError:
            raise PluginError(err.reason)
        else:
            raise PluginError(err)

    return data

def swfverify(url):
    swf = urlget(url)

    if swf[:3] == b"CWS":
        swf = b"F" + swf[1:8] + zlib.decompress(swf[8:])

    h = hmac.new(SWF_KEY, swf, hashlib.sha256)

    return h.hexdigest(), len(swf)

def verifyjson(json, key):
    if not key in json:
        raise PluginError(("Missing '{0}' key in JSON").format(key))

    return json[key]

__all__ = ["ArgumentParser", "urlopen", "urlget", "swfverify", "verifyjson"]
