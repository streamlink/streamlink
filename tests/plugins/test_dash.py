import unittest
from unittest.mock import Mock, patch

import pytest

from streamlink.plugin.plugin import BIT_RATE_WEIGHT_RATIO, LOW_PRIORITY, NO_PRIORITY, NORMAL_PRIORITY
from streamlink.plugins.dash import MPEGDASH
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
@patch("streamlink.stream.DASHStream.parse_manifest")
def test_get_streams(parse_manifest, url, expected):
    session = Mock()
    p = MPEGDASH(session, url)
    p.streams()
    parse_manifest.assert_called_with(session, expected)


class TestPluginMPEGDASH(unittest.TestCase):
    def test_stream_weight(self):
        assert MPEGDASH.stream_weight("720p") == pytest.approx((720, "pixels"))
        assert MPEGDASH.stream_weight("1080p") == pytest.approx((1080, "pixels"))
        assert MPEGDASH.stream_weight("720p+a128k") == pytest.approx((720 + 128, "pixels"))
        assert MPEGDASH.stream_weight("720p+a0k") == pytest.approx((720, "pixels"))
        assert MPEGDASH.stream_weight("a128k") == pytest.approx((128 / BIT_RATE_WEIGHT_RATIO, "bitrate"))
