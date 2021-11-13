import os.path
import unittest
from unittest.mock import patch

from streamlink import Streamlink
from streamlink.api import streams

PluginPath = os.path.join(os.path.dirname(__file__), "plugin")


def get_session():
    s = Streamlink()
    s.load_plugins(PluginPath)
    return s


class TestStreamlinkAPI(unittest.TestCase):
    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_find_test_plugin(self, session):
        self.assertIn("hls", streams("test.se"))

    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_no_streams_exception(self, session):
        self.assertEqual({}, streams("test.se/NoStreamsError"))

    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_no_streams(self, session):
        self.assertEqual({}, streams("test.se/empty"))

    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_stream_type_filter(self, session):
        stream_types = ["hls"]
        available_streams = streams("test.se", stream_types=stream_types)
        self.assertIn("hls", available_streams)
        self.assertNotIn("test", available_streams)
        self.assertNotIn("http", available_streams)

    @patch('streamlink.api.Streamlink', side_effect=get_session)
    def test_stream_type_wildcard(self, session):
        stream_types = ["hls", "*"]
        available_streams = streams("test.se", stream_types=stream_types)
        self.assertIn("hls", available_streams)
        self.assertIn("test", available_streams)
        self.assertIn("http", available_streams)
