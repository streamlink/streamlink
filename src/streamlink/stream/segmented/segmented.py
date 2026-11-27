from __future__ import annotations

import inspect
import queue
import warnings
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event, current_thread
from typing import TYPE_CHECKING, ClassVar, Generic, TypeAlias, TypeVar, cast

from streamlink.buffers import RingBuffer
from streamlink.exceptions import StreamlinkDeprecationWarning
from streamlink.logger import getLogger
from streamlink.stream.stream import StreamIO
from streamlink.utils.thread import NamedThread
from streamlink.utils.times import now


if TYPE_CHECKING:
    from collections.abc import Generator
    from concurrent.futures import Future
    from datetime import datetime

    # noinspection unused-imports
    from typing_extensions import Self  # ruff: ignore[unused-import]

    from streamlink.stream.segmented.segment import Segment
    from streamlink.stream.stream import Stream


log = getLogger(".".join(__name__.split(".")[:-1]))


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


TStream = TypeVar("TStream", bound="Stream")
TReader = TypeVar("TReader", bound="SegmentedStreamReader")
TWriter = TypeVar("TWriter", bound="SegmentedStreamWriter")
TWorker = TypeVar("TWorker", bound="SegmentedStreamWorker")
TSegment = TypeVar("TSegment", bound="Segment")
TResult = TypeVar("TResult")

if TYPE_CHECKING:
    TResultFuture: TypeAlias = Future[TResult | None]
    TQueueItem: TypeAlias = tuple[TSegment, TResultFuture, tuple]


class WriterWorkerInitCompatMeta(type):
    """
    Fix constructor signatures of Writer and Worker subclasses with positional reader arguments
    by injecting a wrapper into the MRO.
    """

    def __new__(mcls, name, bases, namespaces, **kwargs) -> type:
        cls = super().__new__(mcls, name, bases, namespaces, **kwargs)
        if (
            bases
            and (init := getattr(cls, "__init__", None))
            and callable(init)
            and (reader_arg := inspect.signature(init).parameters.get("reader"))
            and reader_arg.kind != reader_arg.KEYWORD_ONLY
        ):

            def __init__(self, reader, **kw):
                bases[0].__init__(self, reader=reader, **kw)

            compat = type(f"_{name}InitCompat", (), {"__init__": __init__})
            cls = super().__new__(mcls, name, (compat, *bases), namespaces, **kwargs)
            warnings.warn(
                f"The constructor of `{name}` uses a deprecated signature. Arguments are keyword-only!",
                StreamlinkDeprecationWarning,
                stacklevel=2,
            )

        return cls


class SegmentedStreamWriter(
    AwaitableMixin,
    NamedThread,
    Generic[
        TStream,
        TReader,
        TSegment,
        TResult,
    ],
    metaclass=WriterWorkerInitCompatMeta,
):
    """
    The base writer thread.
    This thread is responsible for fetching segments, processing them and finally writing the data to the buffer.
    """

    def __init__(
        self,
        *,
        stream: TStream,
        reader: TReader,
        size: int = 20,
        retries: int | None = None,
        threads: int | None = None,
        timeout: float | None = None,
        name: str | None = None,
        **_,
    ) -> None:
        super().__init__(daemon=True, name=name)

        self.closed = False

        self.stream = stream
        self.reader = reader
        self.session = reader.session

        self.retries = retries or self.session.options.get("stream-segment-attempts")
        self.threads = threads or self.session.options.get("stream-segment-threads")
        self.timeout = timeout or self.session.options.get("stream-segment-timeout")

        self.executor = ThreadPoolExecutor(max_workers=self.threads, thread_name_prefix=f"{self.name}-executor")
        self._queue: queue.Queue[TQueueItem | None] = queue.Queue(size)

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

    def _queue_put(self, item: TQueueItem | None) -> None:
        self._queue.put(item, block=True, timeout=1)

    def _queue_get(self) -> TQueueItem | None:
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


class SegmentedStreamWorker(
    AwaitableMixin,
    NamedThread,
    Generic[
        TStream,
        TReader,
        TWriter,
        TSegment,
        TResult,
    ],
    metaclass=WriterWorkerInitCompatMeta,
):
    """
    The base worker thread.
    This thread is responsible for queueing up segments in the writer thread.
    """

    _QUEUE_DEADLINE_MIN = 5.0

    def __init__(
        self,
        *,
        stream: TStream,
        reader: TReader,
        writer: TWriter,
        name: str | None = None,
        **_,
    ) -> None:
        super().__init__(daemon=True, name=name)

        self.closed = False

        self.stream = stream
        self.reader = reader
        self.writer = writer
        self.session = reader.session

        self.sequence: int = -1
        self.duration: float = 0.0
        self.duration_limit: float = self.session.options.get("stream-segmented-duration")

        self._queue_deadline_factor: float = self.session.options.get("stream-segmented-queue-deadline")
        self._queue_last: datetime = now()

    def close(self) -> None:
        """
        Shuts down the thread.
        """

        if self.closed:  # pragma: no cover
            return

        log.debug("Closing worker thread")

        self.closed = True
        self._wait.set()

    @property
    def _queue_deadline_wait(self) -> float:  # pragma: no cover
        """
        The max time in seconds to wait for new segments while fetching data in a polling implementation.
        Will be multiplied by the ``stream-segmented-queue-deadline`` session option in the queue deadline check.
        Needs to be overridden by subclasses which intent to support queue deadlines.
        """
        return 0.0

    def check_queue_deadline(self, queued: bool) -> bool:
        """
        Check whether new segments were queued in a specific time frame during the current iteration of resource fetching,
        so the stream can be stopped early. Should be called in a subclass's ``iter_segments()`` after fetching data.
        :return: True if the stream should be stopped early, False otherwise.
        """

        if queued:
            self._queue_last = now()
            return False

        deadline = max(0.0, self._queue_deadline_wait) * self._queue_deadline_factor
        if deadline <= 0.0:
            return False

        deadline = max(self._QUEUE_DEADLINE_MIN, deadline)
        if now() <= self._queue_last + timedelta(seconds=deadline):
            return False

        log.warning(f"No new segments for more than {deadline:.2f}s. Stopping...")
        return True

    def check_sequence_gap(self, segment: TSegment) -> None:
        size = segment.num - self.sequence
        if size > 0:
            if size > 1:
                msg = f"Sequence gap of {size} segments at position {self.sequence}. "
            else:
                msg = f"Sequence gap of 1 segment at position {self.sequence}. "
            warning = "This is unsupported and will result in incoherent output data."
            log.warning(f"{msg}{warning}")

    def iter_segments(self) -> Generator[TSegment, bool, None]:
        """
        The iterator that generates segments for the worker thread.
        Should be overridden by the inheriting class.
        """

        return
        # noinspection PyUnreachableCode,PyTypeChecker
        yield  # type: ignore[ty:invalid-yield]

    def run(self) -> None:
        self._queue_last = now()

        iter_segments = self.iter_segments()
        queued: bool | None = None

        try:  # ruff: ignore[too-many-statements-in-try-clause]
            while True:
                if queued is None:
                    segment = next(iter_segments)
                else:
                    segment = iter_segments.send(queued)

                if self.closed:  # pragma: no cover
                    break

                log.debug("Queuing %r", segment)

                self.check_sequence_gap(segment)

                self.sequence = segment.num + 1
                self.duration += segment.duration

                self.writer.put(segment)
                queued = True

                if self.duration >= self.duration_limit > 0.0:
                    log.info(f"Stopping stream early after {self.duration_limit:.2f}s")
                    break
        except StopIteration:
            pass

        # End of stream, tells the writer to exit
        self.writer.put(None)
        self.close()


class SegmentedStreamReader(
    StreamIO,
    Generic[
        TStream,
        TWriter,
        TWorker,
        TSegment,
        TResult,
    ],
):
    __writer__: ClassVar[type[SegmentedStreamWriter] | None] = None
    __worker__: ClassVar[type[SegmentedStreamWorker] | None] = None

    writer: TWriter
    worker: TWorker

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        def build_method(name, fn):
            def factory_method(_self, **kw):
                return fn(**kw)

            factory_method.__name__ = name
            return factory_method

        for attr, method in (("__writer__", "_create_writer"), ("__worker__", "_create_worker")):
            if factory := getattr(cls, attr, None):
                setattr(cls, method, build_method(method, factory))
                delattr(cls, attr)
                warnings.warn(
                    f"`{cls.__name__}.{attr}` is deprecated. Implement `{method}()` instead!",
                    StreamlinkDeprecationWarning,
                    stacklevel=3,
                )

    def __init__(self, stream: TStream, name: str | None = None) -> None:
        super().__init__()

        self.stream = stream
        self.session = stream.session

        self.timeout = self.session.options.get("stream-timeout")

        buffer_size = self.session.get_option("ringbuffer-size")
        self.buffer = RingBuffer(buffer_size)

        self._opened = False

        # noinspection unnecessary-cast
        self.writer = cast("TWriter", self._create_writer(name=name, stream=stream, reader=self))
        # noinspection unnecessary-cast
        self.worker = cast("TWorker", self._create_worker(name=name, stream=stream, reader=self, writer=self.writer))

    # noinspection method-may-be-static
    def _create_writer(self, **kwargs):
        return SegmentedStreamWriter["TStream", "Self", "TSegment", "TResult"](**kwargs)

    # noinspection method-may-be-static
    def _create_worker(self, **kwargs):
        return SegmentedStreamWorker["TStream", "Self", "TWriter", "TSegment", "TResult"](**kwargs)

    def open(self) -> None:
        if self._opened:
            return

        self.writer.start()
        self.worker.start()
        self._opened = True

    def close(self) -> None:
        if not self._opened:
            return

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
