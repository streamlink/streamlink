import unittest

# noinspection PyUnresolvedReferences
from requests.utils import DEFAULT_ACCEPT_ENCODING

from streamlink import Streamlink
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
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
