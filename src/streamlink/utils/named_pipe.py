import abc
import logging
import os
import random
import tempfile
import threading

from streamlink.compat import ABC, is_py3, is_win32

if is_win32:
    from ctypes import windll, cast, c_ulong, c_void_p, byref


log = logging.getLogger(__name__)

_lock = threading.Lock()
_id = 0


class NamedPipeBase(ABC):

    def __init__(self):
        global _id
        with _lock:
            _id += 1
            self.name = "streamlinkpipe-{0}-{1}-{2}".format(os.getpid(), _id, random.randint(0, 9999))
        log.info("Creating pipe {0}".format(self.name))
        self._create()

    @abc.abstractmethod
    def _create(self):
        # type: () -> None
        raise NotImplementedError

    @abc.abstractmethod
    def open(self):
        # type: () -> None
        raise NotImplementedError

    @abc.abstractmethod
    def write(self, data):
        # type: () -> int
        raise NotImplementedError

    @abc.abstractmethod
    def close(self):
        # type: () -> None
        raise NotImplementedError


class NamedPipePosix(NamedPipeBase):
    mode = "wb"
    permissions = 0o660
    fifo = None

    def _create(self):
        self.path = os.path.join(tempfile.gettempdir(), self.name)
        os.mkfifo(self.path, self.permissions)

    def open(self):
        self.fifo = open(self.path, self.mode)

    def write(self, data):
        return self.fifo.write(data)

    def close(self):
        if self.fifo is not None:
            self.fifo.close()
            self.fifo = None
            os.unlink(self.path)


class NamedPipeWindows(NamedPipeBase):
    bufsize = 8192
    pipe = None

    PIPE_ACCESS_OUTBOUND = 0x00000002
    PIPE_TYPE_BYTE = 0x00000000
    PIPE_READMODE_BYTE = 0x00000000
    PIPE_WAIT = 0x00000000
    PIPE_UNLIMITED_INSTANCES = 255
    INVALID_HANDLE_VALUE = -1

    @staticmethod
    def _get_last_error():
        error_code = windll.kernel32.GetLastError()
        raise OSError("Named pipe error code 0x{0:08X}".format(error_code))

    def _create(self):
        if is_py3:
            create_named_pipe = windll.kernel32.CreateNamedPipeW
        else:
            create_named_pipe = windll.kernel32.CreateNamedPipeA

        self.path = os.path.join("\\\\.\\pipe", self.name)
        self.pipe = create_named_pipe(
            self.path,
            self.PIPE_ACCESS_OUTBOUND,
            self.PIPE_TYPE_BYTE | self.PIPE_READMODE_BYTE | self.PIPE_WAIT,
            self.PIPE_UNLIMITED_INSTANCES,
            self.bufsize,
            self.bufsize,
            0,
            None
        )
        if self.pipe == self.INVALID_HANDLE_VALUE:
            self._get_last_error()

    def open(self):
        windll.kernel32.ConnectNamedPipe(self.pipe, None)

    def write(self, data):
        written = c_ulong(0)
        windll.kernel32.WriteFile(
            self.pipe,
            cast(data, c_void_p),
            len(data),
            byref(written),
            None
        )
        return written.value

    def close(self):
        if self.pipe is not None:
            windll.kernel32.DisconnectNamedPipe(self.pipe)
            windll.kernel32.CloseHandle(self.pipe)
            self.pipe = None


NamedPipe = NamedPipePosix if not is_win32 else NamedPipeWindows
