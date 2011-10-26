#!/usr/bin/env python3

from livestreamer.compat import urllib, bytes
import hmac, hashlib, zlib

SWF_KEY = b"Genuine Adobe Flash Player 001"

class CommandLine(object):
    def __init__(self, command):
        self.command = command
        self.args = {}

    def arg(self, key, value):
        self.args[key] = value

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

        return cmdline


def swfverify(url):
    fd = urllib.urlopen(url)
    swf = fd.read()
    fd.close()

    if swf[:3] == b"CWS":
        swf = b"F" + swf[1:8] + zlib.decompress(swf[8:])

    h = hmac.new(SWF_KEY, swf, hashlib.sha256)

    return h.hexdigest(), len(swf)
