import io
from threading import Thread

from streamlink.buffers import Buffer, RingBuffer


class StreamIOWrapper(io.IOBase):
    """Wraps file-like objects that are not inheriting from IOBase"""

    def __init__(self, fd):
        self.fd = fd

    def read(self, size=-1):
        return self.fd.read(size)

    def close(self):
        if hasattr(self.fd, "close"):
            self.fd.close()


class StreamIOIterWrapper(io.IOBase):
    """Wraps a iterator and turn it into a file-like object"""

    def __init__(self, iterator):
        self.iterator = iterator
        self.buffer = Buffer()

    def read(self, size=-1):
        if size < 0:
            size = self.buffer.length

        while self.buffer.length < size:
            try:
                chunk = next(self.iterator)
                self.buffer.write(chunk)
            except StopIteration:
                break

        return self.buffer.read(size)

    def close(self):
        pass


class StreamIOThreadWrapper(io.IOBase):
    """Wraps a file-like object in a thread.

    Useful for getting control over read timeout where
    timeout handling is missing or out of our control.
    """

    class Filler(Thread):
        def __init__(self, fd, buffer):
            super().__init__()

            self.error = None
            self.fd = fd
            self.buffer = buffer
            self.daemon = True
            self.running = False

        def run(self):
            self.running = True

            while self.running:
                try:
                    data = self.fd.read(8192)
                except OSError as error:
                    self.error = error
                    break

                if len(data) == 0:
                    break

                self.buffer.write(data)

            self.stop()

        def stop(self):
            self.running = False
            self.buffer.close()

            if hasattr(self.fd, "close"):
                try:
                    self.fd.close()
                except Exception:
                    pass

    def __init__(self, session, fd, timeout=30):
        self.buffer = RingBuffer(session.get_option("ringbuffer-size"))
        self.fd = fd
        self.timeout = timeout

        self.filler = StreamIOThreadWrapper.Filler(self.fd, self.buffer)
        self.filler.start()

    def read(self, size=-1):
        if self.filler.error and self.buffer.length == 0:
            raise self.filler.error

        return self.buffer.read(size, block=self.filler.is_alive(), timeout=self.timeout)

    def close(self):
        self.filler.stop()

        if self.filler.is_alive():
            self.filler.join()


__all__ = ["StreamIOWrapper", "StreamIOIterWrapper", "StreamIOThreadWrapper"]
