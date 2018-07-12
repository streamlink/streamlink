from streamlink import Streamlink
from streamlink.plugins.filmon import FilmOnHLS
from streamlink.stream import AkamaiHDStream
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.stream import RTMPStream
from streamlink.stream import Stream
from streamlink_cli.utils import stream_to_url
import unittest
from tests.mock import patch, PropertyMock


class TestStreamToURL(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def test_base_stream(self):
        stream = Stream(self.session)
        self.assertEqual(None, stream_to_url(stream))
        self.assertRaises(TypeError, stream.to_url)

    def test_http_stream(self):
        expected = "http://test.se/stream"
        stream = HTTPStream(self.session, expected, invalid_arg="invalid")
        self.assertEqual(expected, stream_to_url(stream))
        self.assertEqual(expected, stream.to_url())

    def test_hls_stream(self):
        expected = "http://test.se/stream.m3u8"
        stream = HLSStream(self.session, expected)
        self.assertEqual(expected, stream_to_url(stream))
        self.assertEqual(expected, stream.to_url())

    def test_hds_stream(self):
        stream = HDSStream(self.session, "http://test.se/", "http://test.se/stream.f4m", "http://test.se/stream/1.bootstrap")
        self.assertEqual(None, stream_to_url(stream))
        self.assertRaises(TypeError, stream.to_url)

    def test_akamai_stream(self):
        stream = AkamaiHDStream(self.session, "http://akamai.test.se/stream")
        self.assertEqual(None, stream_to_url(stream))
        self.assertRaises(TypeError, stream.to_url)

    def test_rtmp_stream(self):
        stream = RTMPStream(self.session, {"rtmp": "rtmp://test.se/app/play_path",
                                           "swfVfy": "http://test.se/player.swf",
                                           "swfhash": "test",
                                           "swfsize": 123456,
                                           "playPath": "play_path"})
        expected = "rtmp://test.se/app/play_path playPath=play_path swfUrl=http://test.se/player.swf swfVfy=1"
        self.assertEqual(expected, stream_to_url(stream))
        self.assertEqual(expected, stream.to_url())

    @patch("time.time")
    @patch("streamlink.plugins.filmon.FilmOnHLS.url", new_callable=PropertyMock)
    def test_filmon_stream(self, url, time):
        stream = FilmOnHLS(self.session, channel="test")
        url.return_value = "http://filmon.test.se/test.m3u8"
        stream.watch_timeout = 10
        time.return_value = 1
        expected = "http://filmon.test.se/test.m3u8"

        self.assertEqual(expected, stream_to_url(stream))
        self.assertEqual(expected, stream.to_url())

    @patch("time.time")
    @patch("streamlink.plugins.filmon.FilmOnHLS.url", new_callable=PropertyMock)
    def test_filmon_expired_stream(self, url, time):
        stream = FilmOnHLS(self.session, channel="test")
        url.return_value = "http://filmon.test.se/test.m3u8"
        stream.watch_timeout = 0
        time.return_value = 1

        self.assertEqual(None, stream_to_url(stream))
        self.assertRaises(TypeError, stream.to_url)
