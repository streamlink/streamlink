from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from streamlink.exceptions import StreamlinkDeprecationWarning
from streamlink.stream.segmented.segment import Segment
from streamlink.stream.segmented.segmented import (
    SegmentedStreamReader,
    SegmentedStreamWorker,
    SegmentedStreamWriter,
    log,
)


if TYPE_CHECKING:
    from streamlink.session import Streamlink


def test_logger_name():
    assert log.name == "streamlink.stream.segmented"


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param(
            dict(
                num=1,
                init=False,
                discontinuity=False,
                uri="/path/to/segment.ts?query#fragment",
                duration=4.0,
            ),
            "Segment(num=1, init=False, discontinuity=False, duration=4.000, fileext='ts')",
            id="with-fileext",
        ),
        pytest.param(
            dict(
                num=1,
                init=False,
                discontinuity=False,
                uri="/path/to/segment.other?query#fragment",
                duration=4.0,
            ),
            "Segment(num=1, init=False, discontinuity=False, duration=4.000, fileext=None)",
            id="without-fileext",
        ),
    ],
)
def test_segment_serialization(data: dict, expected: str):
    segment = Segment(**data)
    assert repr(segment) == expected


def test_reader_open_close(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("streamlink.stream.segmented.segmented.RingBuffer", Mock())
    monkeypatch.setattr(SegmentedStreamReader, "_create_writer", Mock())
    monkeypatch.setattr(SegmentedStreamReader, "_create_worker", Mock())

    reader = SegmentedStreamReader[Mock, Mock, Mock, Segment, None](Mock())
    assert not reader._opened
    assert not reader.closed
    assert reader.worker.start.call_count == 0
    assert reader.writer.start.call_count == 0

    reader.close()
    assert not reader.closed
    assert reader.worker.close.call_count == 0
    assert reader.writer.close.call_count == 0

    reader.open()
    assert reader._opened
    assert reader.worker.start.call_count == 1
    assert reader.writer.start.call_count == 1

    reader.open()
    assert reader._opened
    assert reader.worker.start.call_count == 1
    assert reader.writer.start.call_count == 1

    reader.close()
    assert reader.closed
    assert reader.worker.close.call_count == 1
    assert reader.writer.close.call_count == 1


def test_init_compat(recwarn: pytest.WarningsRecorder, session: Streamlink):
    class WriterPositionalReaderArg(SegmentedStreamWriter):
        def __init__(self, reader: SegmentedStreamReader, *args, **kwargs):
            super().__init__(reader, *args, **kwargs)  # type: ignore

    class WorkerPositionalReaderArg(SegmentedStreamWorker):
        def __init__(self, reader: SegmentedStreamReader, *args, **kwargs):
            super().__init__(reader, *args, **kwargs)  # type: ignore

    assert [(record.category, record.filename, str(record.message)) for record in recwarn.list] == [
        (
            StreamlinkDeprecationWarning,
            __file__,
            "The constructor of `WriterPositionalReaderArg` uses a deprecated signature. Arguments are keyword-only!",
        ),
        (
            StreamlinkDeprecationWarning,
            __file__,
            "The constructor of `WorkerPositionalReaderArg` uses a deprecated signature. Arguments are keyword-only!",
        ),
    ]
    recwarn.clear()

    class ReaderPositional(SegmentedStreamReader):
        def _create_writer(self, **kwargs):
            return WriterPositionalReaderArg(**kwargs)

        def _create_worker(self, **kwargs):
            return WorkerPositionalReaderArg(**kwargs)

    class ReaderFactoryAttrs(SegmentedStreamReader):
        __writer__ = SegmentedStreamWriter
        __worker__ = SegmentedStreamWorker

    stream = Mock(session=session)

    reader_default = SegmentedStreamReader["Mock", "Mock", "Mock", "Mock", "Mock"](stream)
    assert isinstance(reader_default.writer, SegmentedStreamWriter)
    assert isinstance(reader_default.worker, SegmentedStreamWorker)
    assert "_SegmentedStreamWriterInitCompat" not in (base.__name__ for base in reader_default.writer.__class__.__mro__)
    assert "_SegmentedStreamWorkerInitCompat" not in (base.__name__ for base in reader_default.worker.__class__.__mro__)

    reader_old_positional = ReaderPositional(stream)
    assert isinstance(reader_old_positional.writer, WriterPositionalReaderArg)
    assert isinstance(reader_old_positional.worker, WorkerPositionalReaderArg)
    assert "_WriterPositionalReaderArgInitCompat" in (base.__name__ for base in reader_old_positional.writer.__class__.__mro__)
    assert "_WorkerPositionalReaderArgInitCompat" in (base.__name__ for base in reader_old_positional.worker.__class__.__mro__)

    reader_factory_attrs = ReaderFactoryAttrs(stream)
    assert isinstance(reader_factory_attrs.writer, SegmentedStreamWriter)
    assert isinstance(reader_factory_attrs.worker, SegmentedStreamWorker)
    assert [(record.category, record.filename, str(record.message)) for record in recwarn.list] == [
        (
            StreamlinkDeprecationWarning,
            __file__,
            "`ReaderFactoryAttrs.__writer__` is deprecated. Implement `_create_writer()` instead!",
        ),
        (
            StreamlinkDeprecationWarning,
            __file__,
            "`ReaderFactoryAttrs.__worker__` is deprecated. Implement `_create_worker()` instead!",
        ),
    ]
