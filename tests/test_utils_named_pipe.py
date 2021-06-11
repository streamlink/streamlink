import os
import stat
import threading
import unittest

from streamlink.compat import is_py3, is_win32
from streamlink.utils.named_pipe import NamedPipe, NamedPipePosix, NamedPipeWindows
from tests.mock import Mock, call, patch

if is_win32:
    from ctypes import windll, create_string_buffer, c_ulong, byref


GENERIC_READ = 0x80000000
OPEN_EXISTING = 3


class ReadNamedPipeThread(threading.Thread):
    def __init__(self, pipe):
        # type: NamedPipe
        if is_py3:
            super().__init__(daemon=True)
        else:
            super(ReadNamedPipeThread, self).__init__()
            self.daemon = True
        self.path = pipe.path
        self.error = None
        self.data = b""
        self.done = threading.Event()

    def run(self):
        try:
            self.read()
        except OSError as err:  # pragma: no cover
            self.error = err
        self.done.set()

    def read(self):
        raise NotImplementedError


class ReadNamedPipeThreadPosix(ReadNamedPipeThread):
    def read(self):
        with open(self.path, "rb") as file:
            while True:
                data = file.read(-1)
                if len(data) == 0:
                    break
                self.data += data


class ReadNamedPipeThreadWindows(ReadNamedPipeThread):
    def read(self):
        if is_py3:
            create_file = windll.kernel32.CreateFileW
        else:
            create_file = windll.kernel32.CreateFileA
        handle = create_file(self.path, GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)
        try:
            while True:
                data = create_string_buffer(NamedPipeWindows.bufsize)
                read = c_ulong(0)
                if not windll.kernel32.ReadFile(handle, data, NamedPipeWindows.bufsize, byref(read), None):  # pragma: no cover
                    raise OSError("Failed reading pipe: {0}".format(windll.kernel32.GetLastError()))
                self.data += data.value
                if read.value != len(data.value):
                    break
        finally:
            windll.kernel32.CloseHandle(handle)


class TestNamedPipe(unittest.TestCase):
    @patch("streamlink.utils.named_pipe._id", 0)
    @patch("streamlink.utils.named_pipe.os.getpid", Mock(return_value=12345))
    @patch("streamlink.utils.named_pipe.random.randint", Mock(return_value=67890))
    @patch("streamlink.utils.named_pipe.NamedPipe._create", Mock(return_value=None))
    @patch("streamlink.utils.named_pipe.log")
    def test_name(self, mock_log):
        NamedPipe()
        NamedPipe()
        self.assertEqual(mock_log.info.mock_calls, [
            call("Creating pipe streamlinkpipe-12345-1-67890"),
            call("Creating pipe streamlinkpipe-12345-2-67890")
        ])


@unittest.skipIf(is_win32, "test only applicable on a POSIX OS")
class TestNamedPipePosix(unittest.TestCase):
    def test_export(self):
        self.assertEqual(NamedPipe, NamedPipePosix)

    @patch("streamlink.utils.named_pipe.os.mkfifo")
    def test_create(self, mock_mkfifo):
        mock_mkfifo.side_effect = OSError()
        with self.assertRaises(OSError):
            NamedPipePosix()
        self.assertEqual(mock_mkfifo.call_args[0][1:], (0o660,))

    def test_close_before_open(self):
        pipe = NamedPipePosix()
        self.assertTrue(stat.S_ISFIFO(os.stat(pipe.path).st_mode))
        pipe.close()
        self.assertTrue(pipe.fifo is None)
        self.assertFalse(os.path.isfile(pipe.path))
        # closing twice doesn't raise
        pipe.close()

    def test_write_before_open(self):
        pipe = NamedPipePosix()
        self.assertTrue(stat.S_ISFIFO(os.stat(pipe.path).st_mode))
        with self.assertRaises(Exception):
            pipe.write(b"foo")
        pipe.close()

    def write_pipe(self, data, pipe):
        if is_py3:
            return pipe.write(data)
        else:
            pipe.write(data)
            return len(data)

    def test_named_pipe(self):
        pipe = NamedPipePosix()
        self.assertTrue(stat.S_ISFIFO(os.stat(pipe.path).st_mode))
        reader = ReadNamedPipeThreadPosix(pipe)
        reader.start()
        pipe.open()
        self.assertEqual(self.write_pipe(b"foo", pipe), 3)
        self.assertEqual(self.write_pipe(b"bar", pipe), 3)
        pipe.close()
        self.assertFalse(os.path.isfile(pipe.path))
        reader.done.wait(4000)
        self.assertEqual(reader.error, None)
        self.assertEqual(reader.data, b"foobar")
        self.assertFalse(reader.is_alive())


@unittest.skipIf(not is_win32, "test only applicable on Windows")
class TestNamedPipeWindows(unittest.TestCase):
    def test_export(self):
        self.assertEqual(NamedPipe, NamedPipeWindows)

    @patch("streamlink.utils.named_pipe.windll.kernel32")
    def test_create(self, mock_kernel32):
        if is_py3:
            create_named_pipe = mock_kernel32.CreateNamedPipeW
        else:
            create_named_pipe = mock_kernel32.CreateNamedPipeA
        create_named_pipe.return_value = NamedPipeWindows.INVALID_HANDLE_VALUE
        mock_kernel32.GetLastError.return_value = 12345
        with self.assertRaises(OSError) as cm:
            NamedPipeWindows()
        self.assertEqual(str(cm.exception), "Named pipe error code 0x00003039")
        self.assertEqual(create_named_pipe.call_args[0][1:], (
            0x00000002,
            0x00000000,
            255,
            8192,
            8192,
            0,
            None
        ))

    def test_close_before_open(self):
        pipe = NamedPipeWindows()
        if is_py3:
            create_file = windll.kernel32.CreateFileW
        else:
            create_file = windll.kernel32.CreateFileA
        handle = create_file(pipe.path, GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)
        self.assertNotEqual(handle, NamedPipeWindows.INVALID_HANDLE_VALUE)
        windll.kernel32.CloseHandle(handle)
        pipe.close()
        handle = create_file(pipe.path, GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)
        self.assertEqual(handle, NamedPipeWindows.INVALID_HANDLE_VALUE)
        # closing twice doesn't raise
        pipe.close()

    def test_named_pipe(self):
        pipe = NamedPipeWindows()
        reader = ReadNamedPipeThreadWindows(pipe)
        reader.start()
        pipe.open()
        self.assertEqual(pipe.write(b"foo"), 3)
        self.assertEqual(pipe.write(b"bar"), 3)
        self.assertEqual(pipe.write(b"\0"), 1)
        reader.done.wait(4000)
        self.assertEqual(reader.error, None)
        self.assertEqual(reader.data, b"foobar")
        self.assertFalse(reader.is_alive())
        pipe.close()
