from livestreamer import options
from livestreamer.utils import urlopen

import os
import pbs
import time
import tempfile

class StreamError(Exception):
    pass

class Stream(object):
    def open(self):
       raise NotImplementedError

class StreamProcess(Stream):
    def __init__(self, params):
        self.params = params or {}
        self.params["_bg"] = True
        self.params["_err"] = open(os.devnull, "w")
        self.errorlog = options.get("errorlog")

    def cmdline(self):
        return str(self.cmd.bake(**self.params))

    def open(self):
        if self.errorlog:
            tmpfile = tempfile.NamedTemporaryFile(prefix="livestreamer",
                                                  suffix=".err", delete=False)
            self.params["_err"] = tmpfile

        stream = self.cmd(**self.params)

        # Wait 0.5 seconds to see if program exited prematurely
        time.sleep(0.5)
        stream.process.poll()

        if stream.process.returncode is not None:
            if self.errorlog:
                raise StreamError(("Error while executing subprocess, error output logged to: {0}").format(tmpfile.name))
            else:
                raise StreamError("Error while executing subprocess")

        return stream.process.stdout

class RTMPStream(StreamProcess):
    def __init__(self, params):
        StreamProcess.__init__(self, params)

        self.rtmpdump = options.get("rtmpdump")
        self.params["flv"] = "-"

        try:
            if self.rtmpdump:
                self.cmd = pbs.Command._create(self.rtmpdump)
            else:
                self.cmd = pbs.rtmpdump
        except pbs.CommandNotFound as err:
            raise StreamError(("Unable to find {0} command").format(str(err)))

    def open(self):
        if "jtv" in self.params and not self._has_jtv_support():
            raise StreamError("Installed rtmpdump does not support --jtv argument")

        return StreamProcess.open(self)

    def _has_jtv_support(self):
        help = self.cmd(help=True, _err_to_out=True)

        for line in help.split("\n"):
            if line[:5] == "--jtv":
                return True

        return False

class HTTPStream(Stream):
    def __init__(self, url):
        self.url = url

    def open(self):
        return urlopen(self.url)

