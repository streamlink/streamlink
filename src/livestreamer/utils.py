from .plugins import PluginError

import argparse
import hashlib
import hmac
import requests
import zlib

SWFKey = b"Genuine Adobe Flash Player 001"
RequestsConfig = { "danger_mode": True }

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

def urlopen(url, method="get", **args):
    if "data" in args and args["data"] is not None:
        method = "post"

    try:
        res = requests.request(method, url, config=RequestsConfig, timeout=15, **args)
    except requests.exceptions.RequestException as err:
        raise PluginError(("Unable to open URL: {url} ({err})").format(url=url, err=str(err)))

    return res

def urlget(url, **args):
    return urlopen(url, method="get", **args)

def swfverify(url):
    res = urlopen(url)
    swf = res.content

    if swf[:3] == b"CWS":
        swf = b"F" + swf[1:8] + zlib.decompress(swf[8:])

    h = hmac.new(SWFKey, swf, hashlib.sha256)

    return h.hexdigest(), len(swf)

def verifyjson(json, key):
    if not key in json:
        raise PluginError(("Missing '{0}' key in JSON").format(key))

    return json[key]

__all__ = ["ArgumentParser", "urlopen", "urlget", "swfverify", "verifyjson"]
