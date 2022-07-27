import threading
import unittest
from unittest.mock import Mock, call, patch

from streamlink.utils.named_pipe import NamedPipe, NamedPipeBase, NamedPipePosix, NamedPipeWindows
from tests import posix_only, windows_only

try:
    from ctypes import windll, create_string_buffer, c_ulong, byref  # type: ignore[attr-defined]
except ImportError:
    pass


GENERIC_READ = 0x80000000
OPEN_EXISTING = 3


class ReadNamedPipeThread(threading.Thread):
    def __init__(self, pipe: NamedPipeBase):
        super().__init__(daemon=True)
        self.path = str(pipe.path)
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
        handle = windll.kernel32.CreateFileW(self.path, GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)
        try:
            while True:
                data = create_string_buffer(NamedPipeWindows.bufsize)
                read = c_ulong(0)
                if not windll.kernel32.ReadFile(handle, data, NamedPipeWindows.bufsize, byref(read), None):  # pragma: no cover
                    raise OSError(f"Failed reading pipe: {windll.kernel32.GetLastError()}")
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


@posix_only
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
        self.assertTrue(pipe.path.is_fifo())
        pipe.close()
        self.assertFalse(pipe.path.is_fifo())
        # closing twice doesn't raise
        pipe.close()

    def test_write_before_open(self):
        pipe = NamedPipePosix()
        self.assertTrue(pipe.path.is_fifo())
        with self.assertRaises(Exception):
            pipe.write(b"foo")
        pipe.close()

    def test_named_pipe(self):
        pipe = NamedPipePosix()
        self.assertTrue(pipe.path.is_fifo())
        reader = ReadNamedPipeThreadPosix(pipe)
        reader.start()
        pipe.open()
        self.assertEqual(pipe.write(b"foo"), 3)
        self.assertEqual(pipe.write(b"bar"), 3)
        pipe.close()
        self.assertFalse(pipe.path.is_fifo())
        reader.done.wait(4000)
        self.assertEqual(reader.error, None)
        self.assertEqual(reader.data, b"foobar")
        self.assertFalse(reader.is_alive())


@windows_only
class TestNamedPipeWindows(unittest.TestCase):
    def test_export(self):
        self.assertEqual(NamedPipe, NamedPipeWindows)

    @patch("streamlink.utils.named_pipe.windll.kernel32")
    def test_create(self, mock_kernel32):
        mock_kernel32.CreateNamedPipeW.return_value = NamedPipeWindows.INVALID_HANDLE_VALUE
        mock_kernel32.GetLastError.return_value = 12345
        with self.assertRaises(OSError) as cm:
            NamedPipeWindows()
        self.assertEqual(str(cm.exception), "Named pipe error code 0x00003039")
        self.assertEqual(mock_kernel32.CreateNamedPipeW.call_args[0][1:], (
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
        handle = windll.kernel32.CreateFileW(str(pipe.path), GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)
        self.assertNotEqual(handle, NamedPipeWindows.INVALID_HANDLE_VALUE)
        windll.kernel32.CloseHandle(handle)
        pipe.close()
        handle = windll.kernel32.CreateFileW(str(pipe.path), GENERIC_READ, 0, None, OPEN_EXISTING, 0, None)
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
