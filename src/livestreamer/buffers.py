from collections import deque
from io import BytesIO
from threading import Event, Lock


class Chunk(BytesIO):
    """A single chunk, part of the buffer."""

    def __init__(self, buf):
        self.length = len(buf)
        BytesIO.__init__(self, buf)

    @property
    def empty(self):
        return self.tell() == self.length


class Buffer(object):
    """Simple buffer for use in single-threaded consumer/filler.

    Stores chunks in a deque to avoid inefficient reallocating
    of large buffers.
    """

    def __init__(self):
        self.chunks = deque()
        self.current_chunk = None
        self.closed = False
        self.length = 0

    def _iterate_chunks(self, size):
        bytes_left = size

        while bytes_left:
            try:
                current_chunk = (self.current_chunk or
                                 Chunk(self.chunks.popleft()))
            except IndexError:
                break

            data = current_chunk.read(bytes_left)
            bytes_left -= len(data)

            if current_chunk.empty:
                self.current_chunk = None
            else:
                self.current_chunk = current_chunk

            yield data

    def write(self, data):
        if not self.closed:
            data = bytes(data)  # Copy so that original buffer may be reused
            self.chunks.append(data)
            self.length += len(data)

    def read(self, size=-1):
        if size < 0 or size > self.length:
            size = self.length

        if not size:
            return b""

        data = b"".join(self._iterate_chunks(size))
        self.length -= len(data)

        return data

    def close(self):
        self.closed = True


class RingBuffer(Buffer):
    """Circular buffer for use in multi-threaded consumer/filler."""

    def __init__(self, size=8192*4):
        Buffer.__init__(self)

        self.buffer_size = size
        self.buffer_lock = Lock()

        self.event_free = Event()
        self.event_free.set()
        self.event_used = Event()

    def _check_events(self):
        if self.length > 0:
            self.event_used.set()
        else:
            self.event_used.clear()

        if self.is_full:
            self.event_free.clear()
        else:
            self.event_free.set()

    def _read(self, size=-1):
        with self.buffer_lock:
            data = Buffer.read(self, size)

            self._check_events()

        return data

    def read(self, size=-1, block=True, timeout=None):
        if block and not self.closed:
            self.event_used.wait(timeout)

            # If the event is still not set it's a timeout
            if not self.event_used.is_set() and self.length == 0:
                raise IOError("Read timeout")

        return self._read(size)

    def write(self, data):
        if self.closed:
            return

        data_left = len(data)
        data_total = len(data)

        while data_left > 0:
            self.event_free.wait()

            if self.closed:
                return

            with self.buffer_lock:
                write_len = min(self.free, data_left)
                written = data_total - data_left

                Buffer.write(self, data[written:written+write_len])
                data_left -= write_len

                self._check_events()

    def resize(self, size):
        with self.buffer_lock:
            self.buffer_size = size

            self._check_events()

    def wait_free(self, timeout=None):
        self.event_free.wait(timeout)

    def wait_used(self, timeout=None):
        self.event_used.wait(timeout)

    def close(self):
        Buffer.close(self)

        # Make sure we don't let a .write() and .read() block forever
        self.event_free.set()
        self.event_used.set()

    @property
    def free(self):
        return max(self.buffer_size - self.length, 0)

    @property
    def is_full(self):
        return self.free == 0

__all__ = ["Buffer", "RingBuffer"]
