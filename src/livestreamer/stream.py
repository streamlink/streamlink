from livestreamer.utils import urlopen

import os
import pbs

class StreamError(Exception):
    pass

class Stream(object):
    def open(self):
       raise NotImplementedError

class RTMPStream(Stream):
    def __init__(self, params):
        self.params = params or {}

    def open(self):
        try:
            rtmpdump = pbs.rtmpdump
        except pbs.CommandNotFound:
            raise StreamError("Unable to find 'rtmpdump' command")

        self.params["flv"] = "-"
        self.params["_bg"] = True
        self.params["_err"] = open(os.devnull, "w")

        stream = rtmpdump(**self.params)

        return stream.process.stdout

class HTTPStream(Stream):
    def __init__(self, url):
        self.url = url

    def open(self):
        return urlopen(self.url)

