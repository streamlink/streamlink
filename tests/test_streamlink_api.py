import pytest

import tests.plugin
from streamlink import Streamlink
from streamlink.api import streams


class TestStreamlinkAPI:
    @pytest.fixture(autouse=True)
    def _session(self, monkeypatch: pytest.MonkeyPatch, session: Streamlink):
        monkeypatch.setattr("streamlink.api.Streamlink", lambda: session)
        session.plugins.load_path(tests.plugin.__path__[0])

    def test_find_test_plugin(self):
        assert "hls" in streams("test.se")

    def test_no_streams_exception(self):
        assert streams("test.se/NoStreamsError") == {}

    def test_no_streams(self):
        assert streams("test.se/empty") == {}

    def test_stream_type_filter(self):
        stream_types = ["hls"]
        available_streams = streams("test.se", stream_types=stream_types)
        assert "hls" in available_streams
        assert "test" not in available_streams
        assert "http" not in available_streams

    def test_stream_type_wildcard(self):
        stream_types = ["hls", "*"]
        available_streams = streams("test.se", stream_types=stream_types)
        assert "hls" in available_streams
        assert "test" in available_streams
        assert "http" in available_streams
