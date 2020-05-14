import unittest

from mock import patch

from streamlink import Streamlink
from streamlink.plugin.plugin import LOW_PRIORITY, NORMAL_PRIORITY, NO_PRIORITY, BIT_RATE_WEIGHT_RATIO
from streamlink.plugins.dash import MPEGDASH


class TestPluginMPEGDASH(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def test_can_handle_url(self):
        # should match
        self.assertTrue(MPEGDASH.can_handle_url("http://example.com/foo.mpd"))
        self.assertTrue(MPEGDASH.can_handle_url("dash://http://www.testing.cat/directe"))
        self.assertTrue(MPEGDASH.can_handle_url("dash://https://www.testing.cat/directe"))

    def test_can_handle_url_negative(self):
        # shouldn't match
        self.assertFalse(MPEGDASH.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(MPEGDASH.can_handle_url("http://www.youtube.com/"))

    def test_priority(self):
        self.assertEqual(MPEGDASH.priority("http://example.com/fpo.mpd"), LOW_PRIORITY)
        self.assertEqual(MPEGDASH.priority("dash://http://example.com/foo.mpd"), NORMAL_PRIORITY)
        self.assertEqual(MPEGDASH.priority("dash://http://example.com/bar"), NORMAL_PRIORITY)
        self.assertEqual(MPEGDASH.priority("http://example.com/bar"), NO_PRIORITY)

    def test_stream_weight(self):
        self.assertAlmostEqual(MPEGDASH.stream_weight("720p"), (720, 'pixels'))
        self.assertAlmostEqual(MPEGDASH.stream_weight("1080p"), (1080, 'pixels'))
        self.assertAlmostEqual(MPEGDASH.stream_weight("720p+a128k"), (720 + 128, 'pixels'))
        self.assertAlmostEqual(MPEGDASH.stream_weight("720p+a0k"), (720, 'pixels'))
        self.assertAlmostEqual(MPEGDASH.stream_weight("a128k"), (128 / BIT_RATE_WEIGHT_RATIO, 'bitrate'))

    @patch("streamlink.stream.DASHStream.parse_manifest")
    def test_get_streams_prefix(self, parse_manifest):
        p = MPEGDASH("dash://http://example.com/foo.mpd")
        p.bind(self.session, 'dash')
        p.streams()
        parse_manifest.assert_called_with(self.session, "http://example.com/foo.mpd")

    @patch("streamlink.stream.DASHStream.parse_manifest")
    def test_get_streams(self, parse_manifest):
        p = MPEGDASH("http://example.com/foo.mpd")
        p.bind(self.session, 'dash')
        p.streams()
        parse_manifest.assert_called_with(self.session, "http://example.com/foo.mpd")
