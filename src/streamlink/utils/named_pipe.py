import abc
import logging
import os
import random
import tempfile
import threading
from pathlib import Path

from streamlink.compat import is_win32

try:
    from ctypes import windll, cast, c_ulong, c_void_p, byref  # type: ignore[attr-defined]
except ImportError:
    pass


log = logging.getLogger(__name__)

_lock = threading.Lock()
_id = 0


class NamedPipeBase(abc.ABC):
    path: Path

    def __init__(self):
        global _id
        with _lock:
            _id += 1
            self.name = f"streamlinkpipe-{os.getpid()}-{_id}-{random.randint(0, 9999)}"
        log.info(f"Creating pipe {self.name}")
        self._create()

    @abc.abstractmethod
    def _create(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def write(self, data) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def close(self) -> None:
        raise NotImplementedError


class NamedPipePosix(NamedPipeBase):
    mode = "wb"
    permissions = 0o660
    fifo = None

    def _create(self):
        self.path = Path(tempfile.gettempdir(), self.name)
        os.mkfifo(self.path, self.permissions)

    def open(self):
        self.fifo = open(self.path, self.mode)

    def write(self, data):
        return self.fifo.write(data)

    def close(self):
        if self.fifo:
            self.fifo.close()
            self.fifo = None
        if self.path.is_fifo():
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
        raise OSError(f"Named pipe error code 0x{error_code:08X}")

    def _create(self):
        self.path = Path("\\\\.\\pipe", self.name)
        self.pipe = windll.kernel32.CreateNamedPipeW(
            str(self.path),
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
