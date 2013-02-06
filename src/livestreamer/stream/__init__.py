from ..compat import bytes, str
from ..packages import pbs as sh
from ..utils import RingBuffer

from threading import Thread

import io
import json
import os
import time
import tempfile

class StreamError(Exception):
    pass


class Stream(object):
    __shortname__ = "stream"

    """
        This is a base class that should be inherited when implementing
        different stream types. Should only be used directly from plugins.
    """

    def __init__(self, session):
        self.session = session

    def __repr__(self):
        return "<Stream()>"

    def __json__(self):
        return dict(type=Stream.shortname())

    def open(self):
        """
            Opens a connection to the stream.
            Returns a file-like object than can be used to read data.
            Raises :exc:`StreamError` on failure.
        """
        raise NotImplementedError

    @property
    def json(self):
        obj = self.__json__()
        return json.dumps(obj)

    @classmethod
    def shortname(cls):
        return cls.__shortname__

class StreamIOWrapper(io.IOBase):
    """Wraps file-like objects that are not inheriting from IOBase"""

    def __init__(self, fd):
        self.fd = fd

    def read(self, size=-1):
        return self.fd.read(size)

    def close(self):
        if hasattr(self.fd, "close"):
            self.fd.close()

class StreamIOThreadWrapper(io.IOBase):
    """
        Wraps a file-like object in a thread.

        Useful for getting control over read timeout where
        timeout handling is missing or out of our control.
    """
    class Filler(Thread):
        def __init__(self, fd, buffer):
            Thread.__init__(self)

            self.error = None
            self.fd = fd
            self.buffer = buffer
            self.daemon = True
            self.running = False

        def run(self):
            self.running = True

            while self.running:
                try:
                    data = self.fd.read(8192)
                except IOError as error:
                    self.error = error
                    break

                if len(data) == 0:
                    break

                self.buffer.write(data)

            self.stop()

        def stop(self):
            self.running = False
            self.buffer.close()

            if hasattr(self.fd, "close"):
                try:
                    self.fd.close()
                except Exception:
                    pass

    def __init__(self, session, fd, timeout=30):
        self.buffer = RingBuffer(session.get_option("ringbuffer-size"))
        self.fd = fd
        self.timeout = timeout

        self.filler = StreamIOThreadWrapper.Filler(self.fd, self.buffer)
        self.filler.start()

    def read(self, size=-1):
        if self.filler.error and self.buffer.length == 0:
            raise self.filler.error

        return self.buffer.read(size, block=self.filler.is_alive(),
                                timeout=self.timeout)

    def close(self):
        self.filler.stop()

        if self.filler.is_alive():
            self.filler.join()

class StreamProcess(Stream):
    def __init__(self, session, params={}, timeout=30):
        Stream.__init__(self, session)

        self.params = params
        self.errorlog = self.session.options.get("errorlog")
        self.timeout = timeout

    def open(self):
        cmd = self._check_cmd()
        params = self.params.copy()
        params["_bg"] = True

        if self.errorlog:
            tmpfile = tempfile.NamedTemporaryFile(prefix="livestreamer",
                                                  suffix=".err", delete=False)
            params["_err"] = tmpfile
        else:
            params["_err"] = open(os.devnull, "wb")

        stream = cmd(**params)

        # Wait 0.5 seconds to see if program exited prematurely
        time.sleep(0.5)

        process_alive = stream.process.returncode is None

        if not process_alive:
            if self.errorlog:
                raise StreamError(("Error while executing subprocess, error output logged to: {0}").format(tmpfile.name))
            else:
                raise StreamError("Error while executing subprocess")

        return StreamIOThreadWrapper(self.session, stream.process.stdout,
                                     timeout=self.timeout)

    def _check_cmd(self):
        try:
            cmd = sh.create_command(self.cmd)
        except sh.CommandNotFound as err:
            raise StreamError(("Unable to find {0} command").format(str(err)))

        return cmd

    def cmdline(self):
        cmd = self._check_cmd()

        return str(cmd.bake(**self.params))

    @classmethod
    def is_usable(cls, cmd):
        try:
            cmd = sh.create_command(cmd)
        except sh.CommandNotFound as err:
            return False

        return True

from .akamaihd import AkamaiHDStream
from .hds import HDSStream
from .hls import HLSStream
from .http import HTTPStream
from .rtmpdump import RTMPStream

__all__ = ["StreamError", "Stream", "StreamProcess", "StreamIOWrapper",
           "AkamaiHDStream", "HLSStream", "HDSStream", "HTTPStream", "RTMPStream"]
