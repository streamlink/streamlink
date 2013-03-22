from .compat import is_win32, is_32bit

import json
import os
import tempfile

if is_win32:
    from ctypes import windll, cast, c_ulong, c_void_p, byref

    PIPE_ACCESS_OUTBOUND = 0x00000002
    PIPE_TYPE_BYTE = 0x00000000
    PIPE_READMODE_BYTE = 0x00000000
    PIPE_WAIT = 0x00000000
    PIPE_UNLIMITED_INSTANCES = 255
    INVALID_HANDLE_VALUE = -1


class NamedPipe(object):
    def __init__(self, name):
        self.fifo = None
        self.pipe = None

        if is_win32:
            self.path = os.path.join("\\\\.\\pipe", name)
            self.pipe = self._create_named_pipe(self.path)
        else:
            self.path = os.path.join(tempfile.gettempdir(), name)
            self._create_fifo(self.path)

    def _create_fifo(self, name):
        os.mkfifo(name, 0o660)

    def _create_named_pipe(self, path):
        bufsize = 8192

        if is_32bit:
            create_named_pipe = windll.kernel32.CreateNamedPipeA
        else:
            create_named_pipe = windll.kernel32.CreateNamedPipeW

        pipe = create_named_pipe(path, PIPE_ACCESS_OUTBOUND,
                                 PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                                 PIPE_UNLIMITED_INSTANCES,
                                 bufsize, bufsize,
                                 0, None)

        if pipe == INVALID_HANDLE_VALUE:
            raise IOError(("error code 0x{0:08X}").format(windll.kernel32.GetLastError()))

        return pipe

    def open(self, mode):
        if not self.pipe:
            self.fifo = open(self.path, mode)

    def write(self, data):
        if self.pipe:
            windll.kernel32.ConnectNamedPipe(self.pipe, None)
            written = c_ulong(0)
            windll.kernel32.WriteFile(self.pipe, cast(data, c_void_p),
                                      len(data), byref(written),
                                      None)
            return written
        else:
            return self.fifo.write(data)

    def close(self):
        if self.pipe:
            windll.kernel32.DisconnectNamedPipe(self.pipe)
        else:
            os.unlink(self.path)


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__json__"):
            return obj.__json__()
        else:
            return json.JSONEncoder.default(self, obj)

__all__ = ["NamedPipe", "JSONEncoder"]
