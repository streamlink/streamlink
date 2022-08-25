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
            self.assertEqual(b[key], value)

    @patch("streamlink.stream.HLSStream.parse_variant_playlist")
    def _test_hls(self, surl, url, mock_parse):
        mock_parse.return_value = {}

        streams = self.session.streams(surl)

        self.assertIn("live", streams)
        mock_parse.assert_called_with(self.session, url)

        stream = streams["live"]
        self.assertIsInstance(stream, HLSStream)
        self.assertEqual(stream.url, url)

    @patch("streamlink.stream.HLSStream.parse_variant_playlist")
    def _test_hlsvariant(self, surl, url, mock_parse):
        mock_parse.return_value = {"best": HLSStream(self.session, url)}

        streams = self.session.streams(surl)

        mock_parse.assert_called_with(self.session, url)

        self.assertNotIn("live", streams)
        self.assertIn("best", streams)

        stream = streams["best"]
        self.assertIsInstance(stream, HLSStream)
        self.assertEqual(stream.url, url)

    def _test_http(self, surl, url, params):
        streams = self.session.streams(surl)

        self.assertIn("live", streams)

        stream = streams["live"]
        self.assertIsInstance(stream, HTTPStream)
        self.assertEqual(stream.url, url)
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
                        "https://hostname.se/auth.php?key=a+value", dict(verify=False, params=dict(key='a value')))

    def test_parse_params(self):
        self.assertEqual({}, parse_params())
        self.assertEqual(
            dict(verify=False, params=dict(key="a value")),
            parse_params("""verify=False params={'key': 'a value'}""")
        )
        self.assertEqual(
            dict(verify=False),
            parse_params("""verify=False""")
        )
        self.assertEqual(
            dict(conn=['B:1', 'S:authMe', 'O:1', 'NN:code:1.23', 'NS:flag:ok', 'O:0']),
            parse_params(""""conn=['B:1', 'S:authMe', 'O:1', 'NN:code:1.23', 'NS:flag:ok', 'O:0']""")
        )

    def test_stream_weight_value(self):
        self.assertEqual((720, "pixels"),
                         stream_weight("720p"))

        self.assertEqual((721, "pixels"),
                         stream_weight("720p+"))

        self.assertEqual((780, "pixels"),
                         stream_weight("720p60"))

    def test_stream_weight(self):
        self.assertGreater(stream_weight("720p+"),
                           stream_weight("720p"))

        self.assertGreater(stream_weight("720p_3000k"),
                           stream_weight("720p_2500k"))

        self.assertGreater(stream_weight("720p60_3000k"),
                           stream_weight("720p_3000k"))

        self.assertGreater(stream_weight("3000k"),
                           stream_weight("2500k"))

        self.assertEqual(stream_weight("720p"),
                         stream_weight("720p"))

        self.assertLess(stream_weight("720p_3000k"),
                        stream_weight("720p+_3000k"))

    def test_stream_weight_and_audio(self):
        self.assertGreater(stream_weight("720p+a256k"),
                           stream_weight("720p+a128k"))

        self.assertGreater(stream_weight("720p+a256k"),
                           stream_weight("720p+a128k"))

        self.assertGreater(stream_weight("720p+a128k"),
                           stream_weight("360p+a256k"))
