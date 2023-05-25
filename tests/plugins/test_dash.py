from unittest.mock import Mock, call

import pytest

from streamlink.plugin.plugin import BIT_RATE_WEIGHT_RATIO, LOW_PRIORITY, NO_PRIORITY, NORMAL_PRIORITY
from streamlink.plugins.dash import MPEGDASH
from streamlink.session import Streamlink
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMPEGDASH(PluginCanHandleUrl):
    __plugin__ = MPEGDASH

    should_match = [
        "example.com/foo.mpd",
        "http://example.com/foo.mpd",
        "https://example.com/foo.mpd",
        "dash://example.com/foo",
        "dash://http://example.com/foo",
        "dash://https://example.com/foo",
    ]


@pytest.mark.parametrize(("url", "priority"), [
    ("http://example.com/foo.mpd", LOW_PRIORITY),
    ("dash://http://example.com/foo.mpd", NORMAL_PRIORITY),
    ("dash://http://example.com/bar", NORMAL_PRIORITY),
    ("http://example.com/bar", NO_PRIORITY),
])
def test_priority(url, priority):
    assert next((matcher.priority for matcher in MPEGDASH.matchers if matcher.pattern.match(url)), NO_PRIORITY) == priority


@pytest.mark.parametrize(("url", "expected"), [
    ("example.com/foo.mpd", "https://example.com/foo.mpd"),
    ("http://example.com/foo.mpd", "http://example.com/foo.mpd"),
    ("https://example.com/foo.mpd", "https://example.com/foo.mpd"),
    ("dash://example.com/foo", "https://example.com/foo"),
    ("dash://http://example.com/foo", "http://example.com/foo"),
    ("dash://https://example.com/foo", "https://example.com/foo"),
])
def test_get_streams(monkeypatch: pytest.MonkeyPatch, session: Streamlink, url, expected):
    mock_parse_manifest = Mock(return_value={})
    monkeypatch.setattr("streamlink.stream.dash.DASHStream.parse_manifest", mock_parse_manifest)

    p = MPEGDASH(session, url)
    p.streams()

    assert mock_parse_manifest.call_args_list == [call(session, expected)]


@pytest.mark.parametrize(("weight", "expected"), [
    ("720p", pytest.approx((720, "pixels"))),
    ("1080p", pytest.approx((1080, "pixels"))),
    ("720p+a128k", pytest.approx((720 + 128, "pixels"))),
    ("720p+a0k", pytest.approx((720, "pixels"))),
    ("a128k", pytest.approx((128 / BIT_RATE_WEIGHT_RATIO, "bitrate"))),
])
def test_stream_weight(weight: str, expected):
    assert MPEGDASH.stream_weight(weight) == expected
