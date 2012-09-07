from .compat import str, is_win32
from .utils import urlget

import os
import pbs
import time
import tempfile

class StreamError(Exception):
    pass

class Stream(object):
    """
        This is a base class that should be inherited when implementing
        different stream types. Should only be used directly from plugins.
    """

    def __init__(self, session):
        self.session = session

    def open(self):
        """
            Opens a connection to the stream.
            Returns a file-like object than can be used to read data.
            Raises :exc:`StreamError` on failure.
        """
        raise NotImplementedError

class StreamProcess(Stream):
    def __init__(self, session, params={}):
        Stream.__init__(self, session)

        self.params = params
        self.params["_bg"] = True
        self.params["_err"] = open(os.devnull, "w")
        self.errorlog = self.session.options.get("errorlog")

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
    def __init__(self, session, params):
        StreamProcess.__init__(self, session, params)

        self.rtmpdump = self.session.options.get("rtmpdump") or (is_win32 and "rtmpdump.exe" or "rtmpdump")
        self.params["flv"] = "-"

        try:
            self.cmd = getattr(pbs, self.rtmpdump)
        except pbs.CommandNotFound as err:
            raise StreamError(("Unable to find {0} command").format(str(err)))

    def open(self):
        if "jtv" in self.params and not self._has_jtv_support():
            raise StreamError("Installed rtmpdump does not support --jtv argument")

        return StreamProcess.open(self)

    def _has_jtv_support(self):
        try:
            help = self.cmd(help=True, _err_to_out=True)
        except pbs.ErrorReturnCode as err:
            raise StreamError(("Error while checking rtmpdump compatibility: {0}").format(str(err.stdout, "ascii")))

        for line in help.split("\n"):
            if line[:5] == "--jtv":
                return True

        return False

class HTTPStream(Stream):
    def __init__(self, session, url, **args):
        Stream.__init__(self, session)

        self.url = url
        self.args = args

    def open(self):
        res = urlget(self.url, prefetch=False,
                     exception=StreamError,
                     **self.args)

        return res.raw

__all__ = ["StreamError", "Stream", "StreamProcess", "RTMPStream", "HTTPStream"]
