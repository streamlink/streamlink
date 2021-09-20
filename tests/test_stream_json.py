import unittest

# noinspection PyUnresolvedReferences
from requests.utils import DEFAULT_ACCEPT_ENCODING

from streamlink import Streamlink
from streamlink.stream.akamaihd import AkamaiHDStream
from streamlink.stream.hds import HDSStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.stream.rtmpdump import RTMPStream
from streamlink.stream.stream import Stream


class TestStreamToJSON(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def test_base_stream(self):
        stream = Stream(self.session)
        self.assertEqual(
            {"type": "stream"},
            stream.__json__()
        )

    def test_http_stream(self):
        url = "http://test.se/stream"
        stream = HTTPStream(self.session, url, headers={"User-Agent": "Test"})
        self.assertEqual(
            {"type": "http",
             "url": url,
             "method": "GET",
             "body": None,
             "headers": {
                 "User-Agent": "Test",
                 "Accept": "*/*",
                 "Accept-Encoding": DEFAULT_ACCEPT_ENCODING,
                 "Connection": "keep-alive",
             }},
            stream.__json__()
        )

    def test_hls_stream(self):
        url = "http://test.se/stream.m3u8"
        master = "http://test.se/master.m3u8"

        stream = HLSStream(self.session, url, headers={"User-Agent": "Test"})
        self.assertEqual(
            {
                "type": "hls",
                "url": url,
                "headers": {
                    "User-Agent": "Test",
                    "Accept": "*/*",
                    "Accept-Encoding": DEFAULT_ACCEPT_ENCODING,
                    "Connection": "keep-alive",
                }
            },
            stream.__json__()
        )

        stream = HLSStream(self.session, url, master, headers={"User-Agent": "Test"})
        self.assertEqual(
            {
                "type": "hls",
                "url": url,
                "headers": {
                    "User-Agent": "Test",
                    "Accept": "*/*",
                    "Accept-Encoding": DEFAULT_ACCEPT_ENCODING,
                    "Connection": "keep-alive",
                },
                "master": master
            },
            stream.__json__()
        )

    def test_hds_stream(self):
        stream = HDSStream(self.session, "http://test.se/", "http://test.se/stream.f4m",
                           "http://test.se/stream/1.bootstrap", headers={"User-Agent": "Test"})
        self.assertEqual(
            {"type": "hds",
             "baseurl": "http://test.se/",
             "bootstrap": "http://test.se/stream/1.bootstrap",
             "url": "http://test.se/stream.f4m",
             "metadata": None,
             "headers": {"User-Agent": "Test"},
             "params": {}},
            stream.__json__()
        )

    def test_akamai_stream(self):
        stream = AkamaiHDStream(self.session, "http://akamai.test.se/stream")
        self.assertEqual(
            {'swf': None,
             'type': 'akamaihd',
             'url': 'http://akamai.test.se/stream'},
            stream.__json__()
        )

    def test_rtmp_stream(self):
        stream = RTMPStream(self.session, {"rtmp": "rtmp://test.se/app/play_path",
                                           "swfVfy": "http://test.se/player.swf",
                                           "swfhash": "test",
                                           "swfsize": 123456,
                                           "playPath": "play_path"})
        self.assertEqual(
            {"type": "rtmp",
             "args": [],
             "params": {"rtmp": "rtmp://test.se/app/play_path",
                        "swfVfy": "http://test.se/player.swf",
                        "swfhash": "test",
                        "swfsize": 123456,
                        "playPath": "play_path"}},
            stream.__json__()
        )
