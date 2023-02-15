import unittest

from streamlink.stream.wrappers import StreamIOIterWrapper


class TestPluginStream(unittest.TestCase):
    def test_iter(self):
        def generator():
            yield b"1" * 8192
            yield b"2" * 4096
            yield b"3" * 2048

        fd = StreamIOIterWrapper(generator())
        assert fd.read(4096) == b"1" * 4096
        assert fd.read(2048) == b"1" * 2048
        assert fd.read(2048) == b"1" * 2048
        assert fd.read(1) == b"2"
        assert fd.read(4095) == b"2" * 4095
        assert fd.read(1536) == b"3" * 1536
        assert fd.read() == b"3" * 512
