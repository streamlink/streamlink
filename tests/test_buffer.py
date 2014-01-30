import unittest

from livestreamer.buffers import Buffer

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


if __name__ == "__main__":
    unittest.main()

