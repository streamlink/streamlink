from __future__ import annotations

import logging
import queue
from collections.abc import Generator
from concurrent import futures
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event, Thread, current_thread
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from streamlink.buffers import RingBuffer
from streamlink.stream.segmented.segment import Segment
from streamlink.stream.stream import Stream, StreamIO


if TYPE_CHECKING:
    try:
        from typing import TypeAlias  # type: ignore[attr-defined]
    except ImportError:
        from typing_extensions import TypeAlias


log = logging.getLogger(".".join(__name__.split(".")[:-1]))


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


TSegment = TypeVar("TSegment", bound=Segment)
TResult = TypeVar("TResult")
TResultFuture: TypeAlias = "Future[TResult | None]"
TQueueItem: TypeAlias = "tuple[TSegment, TResultFuture, tuple]"


class SegmentedStreamWriter(AwaitableMixin, Thread, Generic[TSegment, TResult]):
    """
    The base writer thread.
    This thread is responsible for fetching segments, processing them and finally writing the data to the buffer.
    """

    reader: SegmentedStreamReader[TSegment, TResult]
    stream: Stream

    def __init__(
        self,
        reader: SegmentedStreamReader,
        size: int = 20,
        retries: int | None = None,
        threads: int | None = None,
        timeout: float | None = None,
    ) -> None:
        super().__init__(daemon=True, name=f"Thread-{self.__class__.__name__}")

        self.closed = False

        self.reader = reader
        self.stream = reader.stream
        self.session = reader.session

        self.retries = retries or self.session.options.get("stream-segment-attempts")
        self.threads = threads or self.session.options.get("stream-segment-threads")
        self.timeout = timeout or self.session.options.get("stream-segment-timeout")

        self.executor = ThreadPoolExecutor(max_workers=self.threads)
        self._queue: queue.Queue[TQueueItem] = queue.Queue(size)

    def close(self) -> None:
        """
        Shuts down the thread, its executor and closes the reader (worker thread and buffer).
        """

        if self.closed:  # pragma: no cover
            return

        log.debug("Closing writer thread")

        self.closed = True
        self._wait.set()

        self.reader.close()
        self.executor.shutdown(wait=True, cancel_futures=True)

    def put(self, segment: TSegment | None) -> None:
        """
        Adds a segment to the download pool and write queue.
        """

        if self.closed:  # pragma: no cover
            return

        future: TResultFuture | None
        if segment is None:
            future = None
        else:
            future = self.executor.submit(self.fetch, segment)

        self.queue(segment, future)

    def queue(self, segment: TSegment | None, future: TResultFuture | None, *data) -> None:
        """
        Puts values into a queue but aborts if this thread is closed.
        """

        item = None if segment is None or future is None else (segment, future, data)
        while not self.closed:  # pragma: no branch
            try:
                self._queue_put(item)
                return
            except queue.Full:  # pragma: no cover
                continue

    def _queue_put(self, item: TQueueItem) -> None:
        self._queue.put(item, block=True, timeout=1)

    def _queue_get(self) -> TQueueItem:
        return self._queue.get(block=True, timeout=0.5)

    @staticmethod
    def _future_result(future: TResultFuture) -> TResult | None:
        return future.result(timeout=0.5)

    def fetch(self, segment: TSegment) -> TResult | None:
        """
        Fetches a segment.
        Should be overridden by the inheriting class.
        """

    def write(self, segment: TSegment, result: TResult, *data) -> None:
        """
        Writes a segment to the buffer.
        Should be overridden by the inheriting class.
        """

    def run(self) -> None:
        while not self.closed:
            try:
                item = self._queue_get()
            except queue.Empty:  # pragma: no cover
                continue

            # End of stream
            if item is None:
                break

            segment, future, data = item
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


class SegmentedStreamWorker(AwaitableMixin, Thread, Generic[TSegment, TResult]):
    """
    The base worker thread.
    This thread is responsible for queueing up segments in the writer thread.
    """

    reader: SegmentedStreamReader[TSegment, TResult]
    writer: SegmentedStreamWriter[TSegment, TResult]
    stream: Stream

    def __init__(self, reader: SegmentedStreamReader, **kwargs) -> None:
        super().__init__(daemon=True, name=f"Thread-{self.__class__.__name__}")

        self.closed = False

        self.reader = reader
        self.writer = reader.writer
        self.stream = reader.stream
        self.session = reader.session

    def close(self) -> None:
        """
        Shuts down the thread.
        """

        if self.closed:  # pragma: no cover
            return

        log.debug("Closing worker thread")

        self.closed = True
        self._wait.set()

    def iter_segments(self) -> Generator[TSegment, None, None]:
        """
        The iterator that generates segments for the worker thread.
        Should be overridden by the inheriting class.
        """

        return
        # noinspection PyUnreachableCode
        yield

    def run(self) -> None:
        for segment in self.iter_segments():
            if self.closed:  # pragma: no cover
                break
            self.writer.put(segment)

        # End of stream, tells the writer to exit
        self.writer.put(None)
        self.close()


class SegmentedStreamReader(StreamIO, Generic[TSegment, TResult]):
    __worker__: ClassVar[type[SegmentedStreamWorker]] = SegmentedStreamWorker
    __writer__: ClassVar[type[SegmentedStreamWriter]] = SegmentedStreamWriter

    worker: SegmentedStreamWorker[TSegment, TResult]
    writer: SegmentedStreamWriter[TSegment, TResult]
    stream: Stream

    def __init__(self, stream: Stream) -> None:
        super().__init__()

        self.stream = stream
        self.session = stream.session

        self.timeout = self.session.options.get("stream-timeout")

        buffer_size = self.session.get_option("ringbuffer-size")
        self.buffer = RingBuffer(buffer_size)

        self.writer = self.__writer__(self)
        self.worker = self.__worker__(self)

    def open(self) -> None:
        self.writer.start()
        self.worker.start()

    def close(self) -> None:
        self.worker.close()
        self.writer.close()
        self.buffer.close()

        current = current_thread()
        if current is not self.worker and self.worker.is_alive():  # pragma: no branch
            self.worker.join(timeout=self.timeout)
        if current is not self.writer and self.writer.is_alive():  # pragma: no branch
            self.writer.join(timeout=self.timeout)

        super().close()

    def read(self, size: int) -> bytes:
        return self.buffer.read(
            size,
            block=self.writer.is_alive(),
            timeout=self.timeout,
        )
