from __future__ import annotations

from collections.abc import Mapping
from unittest.mock import Mock

import pytest

from streamlink.stream.stream import Stream
from streamlink_cli.main import resolve_stream_name


@pytest.fixture(scope="module")
def streams():
    a = Stream(Mock())
    b = Stream(Mock())
    c = Stream(Mock())
    d = Stream(Mock())
    e = Stream(Mock())

    return {
        "160p": a,
        "360p": b,
        "480p": c,
        "720p": d,
        "1080p": e,
        "worst": b,
        "best": d,
        "worst-unfiltered": a,
        "best-unfiltered": e,
    }


@pytest.mark.parametrize(
    ("stream_name", "expected"),
    [
        pytest.param("unknown", "unknown"),
        pytest.param("160p", "160p"),
        pytest.param("360p", "360p"),
        pytest.param("480p", "480p"),
        pytest.param("720p", "720p"),
        pytest.param("1080p", "1080p"),
        pytest.param("worst", "360p"),
        pytest.param("best", "720p"),
        pytest.param("worst-unfiltered", "160p"),
        pytest.param("best-unfiltered", "1080p"),
    ],
)
def test_resolve_stream_name(streams: Mapping[str, Stream], stream_name: str, expected: str):
    assert resolve_stream_name(streams, stream_name) == expected
