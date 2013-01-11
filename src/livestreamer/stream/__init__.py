from ..compat import bytes, str, sh, pbs_compat
from ..utils import RingBuffer

from distutils.version import LooseVersion
from locale import getpreferredencoding

import io
import json
import os
import time
import tempfile

DefaultEncoding = getpreferredencoding() or "utf-8"

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


class StreamProcessIO(io.IOBase):
    def __init__(self, session, cmd, params, timeout=30):
        self.cmd = cmd
        self.params = params
        self.session = session
        self.timeout = timeout

        self.fd = RingBuffer(self.session.get_option("ringbuffer-size"))
        self.params["_out_bufsize"] = 8192

        if LooseVersion(sh.__version__) >= LooseVersion("1.07"):
            self.params["_no_out"] = True
            self.params["_no_pipe"] = True

    def open(self):
        def read_callback(data):
            # Work around inconsistent sh behaviour
            if isinstance(data, str):
                data = bytes(data, DefaultEncoding)

            self.fd.write(data)

        self.params["_out"] = read_callback
        self.stream = self.cmd(**self.params)
        self.process = self.stream.process

        return self

    def read(self, size=0):
        if not self.fd:
            return b""

        return self.fd.read(size, block=self.process.alive,
                            timeout=self.timeout)

    def close(self):
        try:
            self.process.kill()
        except:
            pass


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

        if pbs_compat:
            stream = cmd(**params)
        else:
            stream = StreamProcessIO(self.session, cmd, params,
                                     timeout=self.timeout)
            stream.open()

        # Wait 0.5 seconds to see if program exited prematurely
        time.sleep(0.5)

        if pbs_compat:
            process_alive = stream.process.returncode is None
        else:
            process_alive = stream.process.alive

        if not process_alive:
            if self.errorlog:
                raise StreamError(("Error while executing subprocess, error output logged to: {0}").format(tmpfile.name))
            else:
                raise StreamError("Error while executing subprocess")

        if pbs_compat:
            return stream.process.stdout
        else:
            return stream

    def _check_cmd(self):
        try:
            cmd = getattr(sh, self.cmd)
        except sh.CommandNotFound as err:
            raise StreamError(("Unable to find {0} command").format(str(err)))

        return cmd

    def cmdline(self):
        cmd = self._check_cmd()

        return str(cmd.bake(**self.params))

    @classmethod
    def is_usable(cls, cmd):
        try:
            cmd = getattr(sh, cmd)
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
