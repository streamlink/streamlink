import pytest

from streamlink.stream.segmented.segment import Segment
from streamlink.stream.segmented.segmented import log


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
