import unittest

from streamlink.buffers import Buffer, RingBuffer


class TestBuffer(unittest.TestCase):
    def setUp(self):
        self.buffer = Buffer()

    def test_write(self):
        self.buffer.write(b"1" * 8192)
        self.buffer.write(b"2" * 4096)

        self.assertEqual(self.buffer.length, 8192 + 4096)

    def test_read(self):
        self.buffer.write(b"1" * 8192)
        self.buffer.write(b"2" * 4096)

        self.assertEqual(self.buffer.length, 8192 + 4096)
        self.assertEqual(self.buffer.read(4096), b"1" * 4096)
        self.assertEqual(self.buffer.read(4096), b"1" * 4096)
        self.assertEqual(self.buffer.read(), b"2" * 4096)
        self.assertEqual(self.buffer.read(4096), b"")
        self.assertEqual(self.buffer.read(), b"")
        self.assertEqual(self.buffer.length, 0)

    def test_readwrite(self):
        self.buffer.write(b"1" * 8192)
        self.assertEqual(self.buffer.length, 8192)
        self.assertEqual(self.buffer.read(4096), b"1" * 4096)
        self.assertEqual(self.buffer.length, 4096)

        self.buffer.write(b"2" * 4096)
        self.assertEqual(self.buffer.length, 8192)
        self.assertEqual(self.buffer.read(1), b"1")
        self.assertEqual(self.buffer.read(4095), b"1" * 4095)
        self.assertEqual(self.buffer.read(8192), b"2" * 4096)
        self.assertEqual(self.buffer.read(8192), b"")
        self.assertEqual(self.buffer.read(), b"")
        self.assertEqual(self.buffer.length, 0)

    def test_close(self):
        self.buffer.write(b"1" * 8192)
        self.assertEqual(self.buffer.length, 8192)

        self.buffer.close()
        self.buffer.write(b"2" * 8192)
        self.assertEqual(self.buffer.length, 8192)

    def test_reuse_input(self):
        """Objects should be reusable after write()"""

        original = b"original"
        tests = [bytearray(original), memoryview(bytearray(original))]

        for data in tests:
            self.buffer.write(data)
            data[:] = b"reused!!"
            self.assertEqual(self.buffer.read(), original)

    def test_read_empty(self):
        self.assertRaises(
            StopIteration,
            lambda: next(self.buffer._iterate_chunks(10)))


class TestRingBuffer(unittest.TestCase):
    BUFFER_SIZE = 8192 * 4

    def setUp(self):
        self.buffer = RingBuffer(size=self.BUFFER_SIZE)

    def test_write(self):
        self.buffer.write(b"1" * 8192)
        self.buffer.write(b"2" * 4096)

        self.assertEqual(self.buffer.length, 8192 + 4096)

    def test_read(self):
        self.buffer.write(b"1" * 8192)
        self.buffer.write(b"2" * 4096)

        self.assertEqual(self.buffer.length, 8192 + 4096)
        self.assertEqual(self.buffer.read(4096), b"1" * 4096)
        self.assertEqual(self.buffer.read(4096), b"1" * 4096)
        self.assertEqual(self.buffer.read(), b"2" * 4096)
        self.assertEqual(self.buffer.length, 0)

    def test_read_timeout(self):
        self.assertRaises(
            IOError,
            self.buffer.read, timeout=0.1)

    def test_write_after_close(self):
        self.buffer.close()
        self.buffer.write(b"1" * 8192)
        self.assertEqual(self.buffer.length, 0)
        self.assertTrue(self.buffer.closed)

    def test_resize(self):
        self.assertEqual(self.buffer.buffer_size, self.BUFFER_SIZE)
        self.buffer.resize(self.BUFFER_SIZE * 2)
        self.assertEqual(self.buffer.buffer_size, self.BUFFER_SIZE * 2)

    def test_free(self):
        self.assertEqual(self.buffer.free, self.BUFFER_SIZE)
        self.buffer.write(b'1' * 100)
        self.assertEqual(self.buffer.free, self.BUFFER_SIZE - 100)
