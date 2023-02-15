import unittest
from unittest.mock import patch

import requests_mock

from streamlink import Streamlink
from streamlink.plugin.plugin import parse_params, stream_weight
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


class TestPluginStream(unittest.TestCase):
    def setUp(self):
        self.mocker = requests_mock.Mocker()
        self.mocker.start()
        self.mocker.register_uri(requests_mock.ANY, requests_mock.ANY, text="")
        self.session = Streamlink()

    def tearDown(self):
        self.mocker.stop()

    def assertDictHas(self, a, b):
        for key, value in a.items():
            assert b[key] == value

    @patch("streamlink.stream.HLSStream.parse_variant_playlist")
    def _test_hls(self, surl, url, mock_parse):
        mock_parse.return_value = {}

        streams = self.session.streams(surl)

        assert "live" in streams
        mock_parse.assert_called_with(self.session, url)

        stream = streams["live"]
        assert isinstance(stream, HLSStream)
        assert stream.url == url

    @patch("streamlink.stream.HLSStream.parse_variant_playlist")
    def _test_hlsvariant(self, surl, url, mock_parse):
        mock_parse.return_value = {"best": HLSStream(self.session, url)}

        streams = self.session.streams(surl)

        mock_parse.assert_called_with(self.session, url)

        assert "live" not in streams
        assert "best" in streams

        stream = streams["best"]
        assert isinstance(stream, HLSStream)
        assert stream.url == url

    def _test_http(self, surl, url, params):
        streams = self.session.streams(surl)

        assert "live" in streams

        stream = streams["live"]
        assert isinstance(stream, HTTPStream)
        assert stream.url == url
        self.assertDictHas(params, stream.args)

    def test_plugin_hls(self):
        self._test_hls("hls://hostname.se/foo", "https://hostname.se/foo")
        self._test_hls("hls://http://hostname.se/foo", "http://hostname.se/foo")
        self._test_hls("hls://https://hostname.se/foo", "https://hostname.se/foo")

        self._test_hls("hostname.se/playlist.m3u8", "https://hostname.se/playlist.m3u8")
        self._test_hls("http://hostname.se/playlist.m3u8", "http://hostname.se/playlist.m3u8")
        self._test_hls("https://hostname.se/playlist.m3u8", "https://hostname.se/playlist.m3u8")

        self._test_hlsvariant("hls://hostname.se/playlist.m3u8", "https://hostname.se/playlist.m3u8")
        self._test_hlsvariant("hls://http://hostname.se/playlist.m3u8", "http://hostname.se/playlist.m3u8")
        self._test_hlsvariant("hls://https://hostname.se/playlist.m3u8", "https://hostname.se/playlist.m3u8")

    def test_plugin_http(self):
        self._test_http("httpstream://hostname.se/auth.php auth=('test','test2')",
                        "https://hostname.se/auth.php", dict(auth=("test", "test2")))
        self._test_http("httpstream://http://hostname.se/auth.php auth=('test','test2')",
                        "http://hostname.se/auth.php", dict(auth=("test", "test2")))
        self._test_http("httpstream://https://hostname.se/auth.php auth=('test','test2')",
                        "https://hostname.se/auth.php", dict(auth=("test", "test2")))
        self._test_http("httpstream://https://hostname.se/auth.php verify=False params={'key': 'a value'}",
                        "https://hostname.se/auth.php?key=a+value", dict(verify=False, params=dict(key="a value")))

    def test_parse_params(self):
        assert parse_params() \
               == {}
        assert parse_params("verify=False params={'key': 'a value'}") \
               == dict(verify=False, params=dict(key="a value"))
        assert parse_params("verify=False") \
               == dict(verify=False)
        assert parse_params("\"conn=['B:1', 'S:authMe', 'O:1', 'NN:code:1.23', 'NS:flag:ok', 'O:0']") \
               == dict(conn=["B:1", "S:authMe", "O:1", "NN:code:1.23", "NS:flag:ok", "O:0"])

    def test_stream_weight_value(self):
        assert stream_weight("720p") == (720, "pixels")
        assert stream_weight("720p+") == (721, "pixels")
        assert stream_weight("720p60") == (780, "pixels")

    def test_stream_weight(self):
        assert stream_weight("720p+") > stream_weight("720p")
        assert stream_weight("720p_3000k") > stream_weight("720p_2500k")
        assert stream_weight("720p60_3000k") > stream_weight("720p_3000k")
        assert stream_weight("3000k") > stream_weight("2500k")
        assert stream_weight("720p") == stream_weight("720p")
        assert stream_weight("720p_3000k") < stream_weight("720p+_3000k")

    def test_stream_weight_and_audio(self):
        assert stream_weight("720p+a256k") > stream_weight("720p+a128k")
        assert stream_weight("720p+a256k") > stream_weight("720p+a128k")
        assert stream_weight("720p+a128k") > stream_weight("360p+a256k")
