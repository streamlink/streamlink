import os.path
import unittest

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from streamlink import Streamlink
from streamlink.api import streams

PluginPath = os.path.join(os.path.dirname(__file__), "plugins")


def get_session():
    s = Streamlink()
    s.load_plugins(PluginPath)
    return s


class TestStreamlinkAPI(unittest.TestCase):
    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_find_test_plugin(self, session):
        self.assertTrue(
            "rtmp" in streams("test.se")
        )

    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_no_streams_exception(self, session):
        self.assertEqual({}, streams("test.se/NoStreamsError"))

    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_no_streams(self, session):
        self.assertEqual({}, streams("test.se/empty"))

    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_stream_type_filter(self, session):
        stream_types = ["rtmp", "hls"]
        available_streams = streams("test.se", stream_types=stream_types)
        self.assertTrue("rtmp" in available_streams)
        self.assertTrue("hls" in available_streams)
        self.assertTrue("test" not in available_streams)
        self.assertTrue("http" not in available_streams)

    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_stream_type_wildcard(self, session):
        stream_types = ["rtmp", "hls", "*"]
        available_streams = streams("test.se", stream_types=stream_types)
        self.assertTrue("rtmp" in available_streams)
        self.assertTrue("hls" in available_streams)
        self.assertTrue("test" in available_streams)
        self.assertTrue("http" in available_streams)
