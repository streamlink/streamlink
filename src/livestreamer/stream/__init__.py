from ..compat import str
from ..utils import RingBuffer

import os
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
    def __init__(self, session, params={}, timeout=30):
        Stream.__init__(self, session)

        self.params = params
        self.params["_bg"] = True
        self.params["_err"] = open(os.devnull, "w")
        self.params["_out_bufsize"] = 8192
        self.errorlog = self.session.options.get("errorlog")
        self.fd = None
        self.timeout = timeout

    def cmdline(self):
        return str(self.cmd.bake(**self.params))

    def open(self):
        def write_callback(data):
            self.last_data_time = time.time()
            self.fd.write(data)

        self.fd = RingBuffer()
        self.last_data_time = time.time()

        if self.errorlog:
            tmpfile = tempfile.NamedTemporaryFile(prefix="livestreamer",
                                                  suffix=".err", delete=False)
            self.params["_err"] = tmpfile

        self.params["_out"] = write_callback

        stream = self.cmd(**self.params)

        # Wait 0.5 seconds to see if program exited prematurely
        time.sleep(0.5)

        if not stream.process.alive:
            if self.errorlog:
                raise StreamError(("Error while executing subprocess, error output logged to: {0}").format(tmpfile.name))
            else:
                raise StreamError("Error while executing subprocess")

        return self

    def read(self, size=-1):
        if not self.fd:
            return b""

        while self.fd.length < size:
            elapsed_since_read = time.time() - self.last_data_time

            if elapsed_since_read > self.timeout:
                if self.fd.length == 0:
                    raise IOError("Read timeout")
                else:
                    break

            time.sleep(0.05)

        return self.fd.read(size)

from .akamaihd import AkamaiHDStream
from .hls import HLSStream
from .http import HTTPStream
from .rtmpdump import RTMPStream

__all__ = ["StreamError", "Stream", "StreamProcess",
           "AkamaiHDStream", "HLSStream", "HTTPStream", "RTMPStream"]
