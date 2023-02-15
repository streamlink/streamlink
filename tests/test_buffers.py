from threading import Thread

import pytest

from streamlink.buffers import Buffer, RingBuffer
from tests.testutils.handshake import Handshake


class TestBuffer:
    @pytest.fixture()
    def buffer(self):
        return Buffer()

    def test_write(self, buffer: Buffer):
        assert buffer.length == 0
        assert not buffer.written_once

        buffer.write(b"1" * 8192)
        assert buffer.length == 8192
        assert buffer.written_once

        buffer.write(b"2" * 4096)
        assert buffer.length == 8192 + 4096
        assert buffer.written_once

    def test_read(self, buffer: Buffer):
        buffer.write(b"1" * 8192)
        buffer.write(b"2" * 4096)
        assert buffer.length == 8192 + 4096

        assert buffer.read(4096) == b"1" * 4096
        assert buffer.length == 8192

        assert buffer.read(4096) == b"1" * 4096
        assert buffer.length == 4096

        assert buffer.read() == b"2" * 4096
        assert buffer.length == 0

        assert buffer.read(4096) == b""
        assert buffer.read() == b""
        assert buffer.length == 0

    def test_readwrite(self, buffer: Buffer):
        buffer.write(b"1" * 8192)
        assert buffer.length == 8192

        assert buffer.read(4096) == b"1" * 4096
        assert buffer.length == 4096

        buffer.write(b"2" * 4096)
        assert buffer.length == 8192

        assert buffer.read(1) == b"1"
        assert buffer.length == 8191

        assert buffer.read(4095) == b"1" * 4095
        assert buffer.length == 4096

        assert buffer.read(8192) == b"2" * 4096
        assert buffer.length == 0

        assert buffer.read(8192) == b""
        assert buffer.read() == b""
        assert buffer.length == 0

    def test_close(self, buffer: Buffer):
        assert not buffer.closed
        assert not buffer.written_once

        buffer.write(b"1" * 8192)
        assert buffer.length == 8192
        assert buffer.written_once

        buffer.close()
        assert buffer.closed
        assert buffer.written_once

        buffer.write(b"2" * 8192)
        assert buffer.length == 8192
        assert buffer.written_once

        assert buffer.read() == b"1" * 8192
        assert buffer.length == 0

    @pytest.mark.parametrize("data", [
        bytearray(b"0123456789"),
        memoryview(bytearray(b"0123456789")),
    ])
    def test_reuse_input(self, buffer: Buffer, data: bytearray):
        buffer.write(data)
        data[:] = b"9876543210"
        assert buffer.read() == b"0123456789", "Objects are reusable after write()"

    def test_read_empty(self, buffer: Buffer):
        with pytest.raises(StopIteration):
            next(buffer._iterate_chunks(10))


class TestRingBuffer:
    BUFFER_SIZE = 8192 * 4

    @pytest.fixture()
    def buffer(self):
        return RingBuffer(size=self.BUFFER_SIZE)

    def test_write(self, buffer: RingBuffer):
        assert buffer.length == 0

        buffer.write(b"1" * 8192)
        assert buffer.length == 8192

        buffer.write(b"2" * 4096)
        assert buffer.length == 8192 + 4096

    def test_read(self, buffer: RingBuffer):
        buffer.write(b"1" * 8192)
        buffer.write(b"2" * 4096)

        assert buffer.length == 8192 + 4096

        assert buffer.read(4096) == b"1" * 4096
        assert buffer.length == 8192

        assert buffer.read(4096) == b"1" * 4096
        assert buffer.length == 4096

        assert buffer.read() == b"2" * 4096
        assert buffer.length == 0

        assert buffer.read(block=False) == b""
        assert buffer.length == 0

    def test_read_timeout(self, buffer: RingBuffer):
        with pytest.raises(OSError, match=r"^Read timeout$"):
            buffer.read(timeout=0)

    def test_read_after_close(self, buffer: RingBuffer):
        buffer.write(b"1" * 8192)
        buffer.close()
        assert buffer.length == 8192
        assert buffer.closed
        assert buffer.read() == b"1" * 8192

    def test_write_after_close(self, buffer: RingBuffer):
        buffer.close()
        buffer.write(b"1" * 8192)
        assert buffer.length == 0
        assert buffer.closed

    def test_resize(self, buffer: RingBuffer):
        assert buffer.buffer_size == self.BUFFER_SIZE
        buffer.resize(self.BUFFER_SIZE * 2)
        assert buffer.buffer_size == self.BUFFER_SIZE * 2

    def test_free(self, buffer: RingBuffer):
        half = self.BUFFER_SIZE >> 1
        assert buffer.free == self.BUFFER_SIZE

        buffer.write(b"1" * half)
        assert buffer.free == half

        buffer.write(b"1" * half)
        assert buffer.free == 0


class TestThreadedRingBuffer:
    TIMEOUT = 1

    @pytest.fixture()
    def handshake(self):
        handshake = Handshake()
        yield handshake
        assert not handshake._context.error

    @pytest.fixture()
    def buffer(self):
        buffer = RingBuffer(size=4)
        assert not buffer.wait_used(0), "Buffer is not filled initially"
        assert buffer.wait_free(0), "Buffer is free initially"

        return buffer

    def test_read_blocked(self, buffer: RingBuffer, handshake: Handshake):
        def runner():
            nonlocal read
            with handshake():
                read = buffer.read(block=True, timeout=self.TIMEOUT)

        read = None
        runnerthread = Thread(target=runner)
        runnerthread.start()

        buffer.write(b"0123")
        assert buffer.wait_used(0), "Buffer has been filled"
        assert not buffer.wait_free(0), "Buffer is not free anymore"

        assert buffer.read(block=True, timeout=self.TIMEOUT) == b"0123", "Doesn't block reading if data is available"
        assert not buffer.wait_used(0), "Buffer is not filled anymore after reading all data"
        assert buffer.wait_free(0), "Buffer is free again after reading all data"

        assert handshake.wait_ready(self.TIMEOUT)
        assert read is None, "Runner thread hasn't read anything yet"

        handshake.go()
        buffer.write(b"4567")
        assert handshake.wait_done(self.TIMEOUT)
        assert read == b"4567", "Continues once data becomes available"
        assert not buffer.wait_used(0), "Buffer is not filled anymore"
        assert buffer.wait_free(0), "Buffer is free"

        runnerthread.join(self.TIMEOUT)
        assert not runnerthread.is_alive()

    def test_write_blocked(self, buffer: RingBuffer, handshake: Handshake):
        def runner():
            with handshake():
                buffer.write(b"01234567")

        runnerthread = Thread(target=runner)
        runnerthread.start()

        handshake.go()
        assert buffer.wait_used(self.TIMEOUT), "Has written first part"
        assert not buffer.wait_free(0), "Buffer is not free"

        assert buffer.read(block=True, timeout=self.TIMEOUT) == b"0123"
        assert handshake.wait_done(self.TIMEOUT)

        assert buffer.wait_used(self.TIMEOUT), "Has written second part"
        assert not buffer.wait_free(0), "Buffer is still not free"

        assert buffer.read(block=True, timeout=self.TIMEOUT) == b"4567"
        assert not buffer.wait_used(0), "Buffer is not filled anymore"
        assert buffer.wait_free(0), "Buffer is free again"

        runnerthread.join(self.TIMEOUT)
        assert not runnerthread.is_alive()

    def test_write_blocked_close(self, buffer: RingBuffer, handshake: Handshake):
        def runner():
            with handshake():
                buffer.write(b"01234567")

        runnerthread = Thread(target=runner)
        runnerthread.start()

        handshake.go()
        assert buffer.wait_used(self.TIMEOUT), "Has written first part"
        assert not buffer.wait_free(0), "Buffer is not free"

        buffer.close()
        assert handshake.wait_done(self.TIMEOUT), "Has stopped writing"

        assert buffer.read(block=True, timeout=self.TIMEOUT) == b"0123"
        assert not buffer.wait_used(0), "Buffer is not filled"
        assert buffer.wait_free(0), "Buffer is free"

        runnerthread.join(self.TIMEOUT)
        assert not runnerthread.is_alive()
