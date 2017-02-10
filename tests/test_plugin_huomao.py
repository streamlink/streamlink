# Unit tests accompanying the Huomao Streamlink plugin.

import unittest
import re

from streamlink.plugin.api import http
from streamlink.plugins.huomao import Huomao

class TestPluginHuomao(unittest.TestCase):

    def setUp(self):

        # Create a mock source HTML with some example data:
        #   room_id             = 123456
        #   stream_id           = 9qsvyF24659
        #   stream_url          = http://live-ws.huomaotv.cn/live/
        #   stream_quality      = source, _720 and _480
        #   stream_quality_name = source, 720 and 480
        self.mock_html = """
            <input id="html_stream" value="9qsvyF24659" type="hidden">
            <!--            urls:{-->
            <!--                1: 'http://live-ws.huomaotv.cn/live/'+stream+'/playlist.m3u8',-->
            <!--                2: 'http://live-ws.huomaotv.cn/live/'+stream+'_720/playlist.m3u8',-->
            <!--                3: 'http://live-ws.huomaotv.cn/live/'+stream+'_480/playlist.m3u8'-->
            <!--            },-->
        """

        # Create a mock Huomao object.
        self.mock_huomao = Huomao("http://www.huomao.com/123456/")

    def tearDown(self):
        self.mock_html = None
        self.mock_huomao = None

    def test_get_stream_id(self):

        # Assert that the stream_id from is correctly extracted from the mock HTML.
        self.assertEqual(self.mock_huomao.get_stream_id(self.mock_html), "9qsvyF24659")

    def test_get_stream_quality(self):

        # Assert that the stream_url, stream_quality and stream_quality_name
        # is correctly extracted from the mock HTML.
        self.assertEqual(self.mock_huomao.get_stream_info(self.mock_html), [
            ["http://live-ws.huomaotv.cn/live/", "", "source"],
            ["http://live-ws.huomaotv.cn/live/", "_720", "720"],
            ["http://live-ws.huomaotv.cn/live/", "_480", "480"]
        ])

    def test_can_handle_url(self):

        # Assert that an URL containing the http:// prefix is correctly read.
        self.assertTrue(Huomao.can_handle_url("http://www.huomao.com/123456"))
        self.assertTrue(Huomao.can_handle_url("http://www.huomao.tv/123456"))
        self.assertTrue(Huomao.can_handle_url("http://huomao.com/123456"))
        self.assertTrue(Huomao.can_handle_url("http://huomao.tv/123456"))

        # Assert that an URL containing the https:// prefix is correctly read.
        self.assertTrue(Huomao.can_handle_url("https://www.huomao.com/123456"))
        self.assertTrue(Huomao.can_handle_url("https://www.huomao.tv/123456"))
        self.assertTrue(Huomao.can_handle_url("https://huomao.com/123456"))
        self.assertTrue(Huomao.can_handle_url("https://huomao.tv/123456"))

        # Assert that an URL without the http(s):// prefix is correctly read.
        self.assertTrue(Huomao.can_handle_url("www.huomao.com/123456"))
        self.assertTrue(Huomao.can_handle_url("www.huomao.tv/123456"))

        # Assert that an URL without the www prefix is correctly read.
        self.assertTrue(Huomao.can_handle_url("huomao.com/123456"))
        self.assertTrue(Huomao.can_handle_url("huomao.tv/123456"))

        # Assert that an URL without a room_id can't be read.
        self.assertFalse(Huomao.can_handle_url("http://www.huomao.com/"))
        self.assertFalse(Huomao.can_handle_url("http://www.huomao.tv/"))
        self.assertFalse(Huomao.can_handle_url("http://huomao.com/"))
        self.assertFalse(Huomao.can_handle_url("http://huomao.tv/"))
        self.assertFalse(Huomao.can_handle_url("https://www.huomao.com/"))
        self.assertFalse(Huomao.can_handle_url("https://www.huomao.tv/"))
        self.assertFalse(Huomao.can_handle_url("https://huomao.com/"))
        self.assertFalse(Huomao.can_handle_url("https://huomao.tv/"))
        self.assertFalse(Huomao.can_handle_url("www.huomao.com/"))
        self.assertFalse(Huomao.can_handle_url("www.huomao.tv/"))
        self.assertFalse(Huomao.can_handle_url("huomao.tv/"))
        self.assertFalse(Huomao.can_handle_url("huomao.tv/"))

        # Assert that an URL without "huomao" can't be read.
        self.assertFalse(Huomao.can_handle_url("http://www.youtube.com/123456"))
        self.assertFalse(Huomao.can_handle_url("http://www.youtube.tv/123456"))
        self.assertFalse(Huomao.can_handle_url("http://youtube.com/123456"))
        self.assertFalse(Huomao.can_handle_url("http://youtube.tv/123456"))
        self.assertFalse(Huomao.can_handle_url("https://www.youtube.com/123456"))
        self.assertFalse(Huomao.can_handle_url("https://www.youtube.tv/123456"))
        self.assertFalse(Huomao.can_handle_url("https://youtube.com/123456"))
        self.assertFalse(Huomao.can_handle_url("https://youtube.tv/123456"))

# Possibility to run unittest separately as a normal python script.
if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPluginHuomao)
    unittest.TextTestRunner(verbosity = 2).run(suite)
