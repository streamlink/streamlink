import os
import tempfile

from ..compat import is_win32, is_py3


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

        if is_py3:
            create_named_pipe = windll.kernel32.CreateNamedPipeW
        else:
            create_named_pipe = windll.kernel32.CreateNamedPipeA

        pipe = create_named_pipe(path, PIPE_ACCESS_OUTBOUND,
                                 PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                                 PIPE_UNLIMITED_INSTANCES,
                                 bufsize, bufsize,
                                 0, None)

        if pipe == INVALID_HANDLE_VALUE:
            error_code = windll.kernel32.GetLastError()
            raise IOError("Error code 0x{0:08X}".format(error_code))

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
            self.fifo.close()
            os.unlink(self.path)
