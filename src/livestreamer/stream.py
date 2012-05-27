from livestreamer.utils import urlopen

import os
import pbs

class StreamError(Exception):
    pass

class Stream(object):
    def open(self):
       raise NotImplementedError

class StreamProcess(Stream):
    def __init__(self, params):
        self.params = params or {}

    def cmdline(self):
        return str(self.cmd.bake(**self.params))

    def open(self):
        stream = self.cmd(**self.params)

        return stream.process.stdout

class RTMPStream(StreamProcess):
    def __init__(self, params):
        StreamProcess.__init__(self, params)

        self.params["flv"] = "-"
        self.params["_bg"] = True
        self.params["_err"] = open(os.devnull, "w")

        try:
            self.cmd = pbs.rtmpdump
        except pbs.CommandNotFound:
            raise StreamError("Unable to find 'rtmpdump' command")

class HTTPStream(Stream):
    def __init__(self, url):
        self.url = url

    def open(self):
        return urlopen(self.url)

