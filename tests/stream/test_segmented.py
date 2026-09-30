from unittest.mock import Mock

import pytest

from streamlink.stream.segmented.segment import Segment
from streamlink.stream.segmented.segmented import SegmentedStreamReader, log


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
    class FakeSegmentedStreamReader(SegmentedStreamReader[Segment, None]):
        worker: Mock
        writer: Mock

    monkeypatch.setattr("streamlink.stream.segmented.segmented.RingBuffer", Mock())
    monkeypatch.setattr(FakeSegmentedStreamReader, "__worker__", Mock())
    monkeypatch.setattr(FakeSegmentedStreamReader, "__writer__", Mock())

    reader = FakeSegmentedStreamReader(Mock())
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
