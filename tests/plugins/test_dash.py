import unittest
from unittest.mock import Mock, patch

import pytest

from streamlink.plugin.plugin import BIT_RATE_WEIGHT_RATIO, LOW_PRIORITY, NORMAL_PRIORITY, NO_PRIORITY
from streamlink.plugins.dash import MPEGDASH
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMPEGDASH(PluginCanHandleUrl):
    __plugin__ = MPEGDASH

    should_match = [
        "http://example.com/foo.mpd",
        "dash://http://www.testing.cat/directe",
        "dash://https://www.testing.cat/directe",
    ]


@pytest.mark.parametrize("url,priority", [
    ("http://example.com/foo.mpd", LOW_PRIORITY),
    ("dash://http://example.com/foo.mpd", NORMAL_PRIORITY),
    ("dash://http://example.com/bar", NORMAL_PRIORITY),
    ("http://example.com/bar", NO_PRIORITY),
])
def test_priority(url, priority):
    session = Mock()
    MPEGDASH.bind(session, "tests.plugins.test_dash")
    assert next((matcher.priority for matcher in MPEGDASH.matchers if matcher.pattern.match(url)), NO_PRIORITY) == priority


class TestPluginMPEGDASH(unittest.TestCase):
    def test_stream_weight(self):
        self.assertAlmostEqual(MPEGDASH.stream_weight("720p"), (720, 'pixels'))
        self.assertAlmostEqual(MPEGDASH.stream_weight("1080p"), (1080, 'pixels'))
        self.assertAlmostEqual(MPEGDASH.stream_weight("720p+a128k"), (720 + 128, 'pixels'))
        self.assertAlmostEqual(MPEGDASH.stream_weight("720p+a0k"), (720, 'pixels'))
        self.assertAlmostEqual(MPEGDASH.stream_weight("a128k"), (128 / BIT_RATE_WEIGHT_RATIO, 'bitrate'))

    @patch("streamlink.stream.DASHStream.parse_manifest")
    def test_get_streams_prefix(self, parse_manifest):
        session = Mock()
        MPEGDASH.bind(session, "tests.plugins.test_dash")
        p = MPEGDASH("dash://http://example.com/foo.mpd")
        p.streams()
        parse_manifest.assert_called_with(session, "http://example.com/foo.mpd")

    @patch("streamlink.stream.DASHStream.parse_manifest")
    def test_get_streams(self, parse_manifest):
        session = Mock()
        MPEGDASH.bind(session, "tests.plugins.test_dash")
        p = MPEGDASH("http://example.com/foo.mpd")
        p.streams()
        parse_manifest.assert_called_with(session, "http://example.com/foo.mpd")
