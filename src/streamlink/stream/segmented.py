import logging
import queue
from concurrent import futures
from concurrent.futures import Future, ThreadPoolExecutor
from sys import version_info
from threading import Event, Thread, current_thread
from typing import Any, Optional

from streamlink.buffers import RingBuffer
from streamlink.stream.stream import Stream, StreamIO


log = logging.getLogger(__name__)


class CompatThreadPoolExecutor(ThreadPoolExecutor):
    if version_info < (3, 9):
        def shutdown(self, wait=True, cancel_futures=False):  # pragma: no cover
            with self._shutdown_lock:
                self._shutdown = True
                if cancel_futures:
                    # Drain all work items from the queue, and then cancel their
                    # associated futures.
                    while True:
                        try:
                            work_item = self._work_queue.get_nowait()
                        except queue.Empty:
                            break
                        if work_item is not None:
                            work_item.future.cancel()

                # Send a wake-up to prevent threads calling
                # _work_queue.get(block=True) from permanently blocking.
                self._work_queue.put(None)
            if wait:
                for t in self._threads:
                    t.join()


class AwaitableMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wait = Event()

    def wait(self, time: float) -> bool:
        """
        Pause the thread for a specified time.
        Return False if interrupted by another thread and True if the time runs out normally.
        """
        return not self._wait.wait(time)


class SegmentedStreamWorker(AwaitableMixin, Thread):
    """The general worker thread.

    This thread is responsible for queueing up segments in the
    writer thread.
    """

    reader: "SegmentedStreamReader"
    writer: "SegmentedStreamWriter"
    stream: "Stream"

    def __init__(self, reader: "SegmentedStreamReader", **kwargs):
        super().__init__(daemon=True, name=f"Thread-{self.__class__.__name__}")
        self.closed = False
        self.reader = reader
        self.writer = reader.writer
        self.stream = reader.stream
        self.session = reader.session

    def close(self):
        """Shuts down the thread."""
        if self.closed:  # pragma: no cover
            return

        log.debug("Closing worker thread")

        self.closed = True
        self._wait.set()

    def iter_segments(self):
        """The iterator that generates segments for the worker thread.

        Should be overridden by the inheriting class.
        """
        return
        yield

    def run(self):
        for segment in self.iter_segments():
            if self.closed:  # pragma: no cover
                break
            self.writer.put(segment)

        # End of stream, tells the writer to exit
        self.writer.put(None)
        self.close()


class SegmentedStreamWriter(AwaitableMixin, Thread):
    """The writer thread.

    This thread is responsible for fetching segments, processing them
    and finally writing the data to the buffer.
    """

    reader: "SegmentedStreamReader"
    stream: "Stream"

    def __init__(self, reader: "SegmentedStreamReader", size=20, retries=None, threads=None, timeout=None):
        super().__init__(daemon=True, name=f"Thread-{self.__class__.__name__}")
        self.closed = False
        self.reader = reader
        self.stream = reader.stream
        self.session = reader.session

        if not retries:
            retries = self.session.options.get("stream-segment-attempts")

        if not threads:
            threads = self.session.options.get("stream-segment-threads")

        if not timeout:
            timeout = self.session.options.get("stream-segment-timeout")

        self.retries = retries
        self.timeout = timeout
        self.threads = threads
        self.executor = CompatThreadPoolExecutor(max_workers=self.threads)
        self.futures: queue.Queue[Future] = queue.Queue(size)

    def close(self):
        """Shuts down the thread, its executor and closes the reader (worker thread and buffer)."""
        if self.closed:  # pragma: no cover
            return

        log.debug("Closing writer thread")

        self.closed = True
        self._wait.set()

        self.reader.close()
        self.executor.shutdown(wait=True, cancel_futures=True)

    def put(self, segment):
        """Adds a segment to the download pool and write queue."""
        if self.closed:  # pragma: no cover
            return

        if segment is None:
            future = None
        else:
            future = self.executor.submit(self.fetch, segment, retries=self.retries)

        self.queue(segment, future)

    def queue(self, segment: Any, future: Optional[Future], *data):
        """Puts values into a queue but aborts if this thread is closed."""
        while not self.closed:  # pragma: no branch
            try:
                self._futures_put((segment, future, *data))
                return
            except queue.Full:  # pragma: no cover
                continue

    def _futures_put(self, item):
        self.futures.put(item, block=True, timeout=1)

    def _futures_get(self):
        return self.futures.get(block=True, timeout=0.5)

    @staticmethod
    def _future_result(future: Future):
        return future.result(timeout=0.5)

    def fetch(self, segment):
        """Fetches a segment.

        Should be overridden by the inheriting class.
        """

    def write(self, segment, result, *data):
        """Writes a segment to the buffer.

        Should be overridden by the inheriting class.
        """

    def run(self):
        while not self.closed:
            try:
                segment, future, *data = self._futures_get()
            except queue.Empty:  # pragma: no cover
                continue

            # End of stream
            if future is None:
                break

            while not self.closed:  # pragma: no branch
                try:
                    result = self._future_result(future)
                except futures.TimeoutError:  # pragma: no cover
                    continue
                except futures.CancelledError:  # pragma: no cover
                    break

                if result is not None:  # pragma: no branch
                    self.write(segment, result, *data)

                break

        self.close()


class SegmentedStreamReader(StreamIO):
    __worker__ = SegmentedStreamWorker
    __writer__ = SegmentedStreamWriter

    worker: "SegmentedStreamWorker"
    writer: "SegmentedStreamWriter"
    stream: "Stream"

    def __init__(self, stream: "Stream", timeout=None):
        super().__init__()
        self.stream = stream
        self.session = stream.session
        self.timeout = timeout or self.session.options.get("stream-timeout")

        buffer_size = self.session.get_option("ringbuffer-size")
        self.buffer = RingBuffer(buffer_size)
        self.writer = self.__writer__(self)
        self.worker = self.__worker__(self)

    def open(self):
        self.writer.start()
        self.worker.start()

    def close(self):
        self.worker.close()
        self.writer.close()
        self.buffer.close()

        current = current_thread()
        if current is not self.worker:  # pragma: no branch
            self.worker.join(timeout=self.timeout)
        if current is not self.writer:  # pragma: no branch
            self.writer.join(timeout=self.timeout)

        super().close()

    def read(self, size):
        return self.buffer.read(
            size,
            block=self.writer.is_alive(),
            timeout=self.timeout,
        )
