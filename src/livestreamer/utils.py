#!/usr/bin/env python3

from livestreamer.compat import urllib, bytes
from livestreamer.plugins import PluginError
import hmac, hashlib, zlib, argparse

SWF_KEY = b"Genuine Adobe Flash Player 001"

class CommandLine(object):
    def __init__(self, command):
        self.command = command
        self.args = {}
        self.pipe = None

    def format(self):
        args = []

        for key, value in self.args.items():
            if value == True:
                args.append(("--{0}").format(key))
            else:
                escaped = str(value).replace('"', '\\"').replace("$", "\$").replace("`", "\`")
                args.append(("--{0} \"{1}\"").format(key, escaped))

        args = (" ").join(args)
        cmdline = ("{0} {1}").format(self.command, args)

        if self.pipe:
            cmdline += (" | {0}").format(self.pipe)

        return cmdline

class ArgumentParser(argparse.ArgumentParser):
    def convert_arg_line_to_args(self, line):
        split = line.find("=")
        key = line[:split].strip()
        val = line[split+1:].strip()
        yield "--%s=%s" % (key, val)

def urlget(url, data=None, timeout=None, opener=None):
    try:
        if opener is not None:
            fd = opener.open(url)
        else:
            fd = urllib.urlopen(url, data, timeout)

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

