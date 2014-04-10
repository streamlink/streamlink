from threading import Thread, Event

from .stream import StreamIO
from ..buffers import RingBuffer
from ..compat import queue



class SegmentedStreamWorker(Thread):
    """The general worker thread.

    This thread is responsible for queueing up segments in the
    writer thread.
    """

    def __init__(self, reader):
        self.closed = False
        self.reader = reader
        self.writer = reader.writer
        self.stream = reader.stream
        self.session = reader.stream.session
        self.logger = reader.logger

        self._wait = None

        Thread.__init__(self)
        self.daemon = True

    def close(self):
        """Shuts down the thread."""
        if not self.closed:
            self.logger.debug("Closing worker thread")

        self.closed = True
        if self._wait:
            self._wait.set()

    def wait(self, time):
        """Pauses the thread."""
        self._wait = Event()
        self._wait.wait(time)

    def iter_segments(self):
        """The iterator that generates segments for the worker thread.

        Should be overridden by the inheriting class.
        """
        return
        yield

    def run(self):
        for segment in self.iter_segments():
            self.writer.put(segment)

        # End of stream, tells the writer to exit
        self.writer.put(None)
        self.close()


class SegmentedStreamWriter(Thread):
    """The writer thread.

    This thread is responsible for fetching segments, processing them
    and finally writing the data to the buffer.
    """

    def __init__(self, reader, size=10):
        self.closed = False
        self.queue = queue.Queue(size)
        self.reader = reader
        self.stream = reader.stream
        self.session = reader.stream.session
        self.logger = reader.logger

        Thread.__init__(self)
        self.daemon = True

    def close(self):
        """Shuts down the thread."""
        if not self.closed:
            self.logger.debug("Closing writer thread")

        self.closed = True
        self.reader.buffer.close()

    def put(self, segment):
        """Add a segment to the queue."""
        while not self.closed:
            try:
                self.queue.put(segment, block=True, timeout=1)
                break
            except queue.Full:
                continue

    def write(self, segment):
        """Write the segment to the buffer.

        Should be overridden by the inheriting class.
        """
        pass

    def run(self):
        while not self.closed:
            try:
                segment = self.queue.get(block=True, timeout=0.5)
            except queue.Empty:
                continue

            if segment is not None:
                self.write(segment)
            else:
                break

        self.close()


class SegmentedStreamReader(StreamIO):
    __worker__ = SegmentedStreamWorker
    __writer__ = SegmentedStreamWriter

    def __init__(self, stream, timeout=60):
        StreamIO.__init__(self)

        self.session = stream.session
        self.stream = stream
        self.timeout = timeout

    def open(self):
        buffer_size = self.session.get_option("ringbuffer-size")
        self.buffer = RingBuffer(buffer_size)
        self.writer = self.__writer__(self)
        self.worker = self.__worker__(self)

        self.writer.start()
        self.worker.start()

    def close(self):
        self.worker.close()
        self.writer.close()

        for thread in (self.worker, self.writer):
            if thread.is_alive():
                thread.join()

        self.buffer.close()

    def read(self, size):
        if not self.buffer:
            return b""

        return self.buffer.read(size, block=self.writer.is_alive(),
                                timeout=self.timeout)



