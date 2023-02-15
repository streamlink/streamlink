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
    @patch("streamlink.api.Streamlink", side_effect=get_session)
    def test_find_test_plugin(self, session):
        assert "hls" in streams("test.se")

    @patch("streamlink.api.Streamlink", side_effect=get_session)
    def test_no_streams_exception(self, session):
        assert streams("test.se/NoStreamsError") == {}

    @patch("streamlink.api.Streamlink", side_effect=get_session)
    def test_no_streams(self, session):
        assert streams("test.se/empty") == {}

    @patch("streamlink.api.Streamlink", side_effect=get_session)
    def test_stream_type_filter(self, session):
        stream_types = ["hls"]
        available_streams = streams("test.se", stream_types=stream_types)
        assert "hls" in available_streams
        assert "test" not in available_streams
        assert "http" not in available_streams

    @patch("streamlink.api.Streamlink", side_effect=get_session)
    def test_stream_type_wildcard(self, session):
        stream_types = ["hls", "*"]
        available_streams = streams("test.se", stream_types=stream_types)
        assert "hls" in available_streams
        assert "test" in available_streams
        assert "http" in available_streams
