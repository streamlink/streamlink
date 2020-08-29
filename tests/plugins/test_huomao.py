import unittest

from streamlink.plugins.huomao import Huomao


class TestPluginHuomao(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            # Assert that an URL containing the http:// prefix is correctly read.
            "http://www.huomao.com/123456",
            "http://www.huomao.tv/123456",
            "http://huomao.com/123456",
            "http://huomao.tv/123456",
            "http://www.huomao.com/video/v/123456",
            "http://www.huomao.tv/video/v/123456",
            "http://huomao.com/video/v/123456",
            "http://huomao.tv/video/v/123456",

            # Assert that an URL containing the https:// prefix is correctly read.
            "https://www.huomao.com/123456",
            "https://www.huomao.tv/123456",
            "https://huomao.com/123456",
            "https://huomao.tv/123456",
            "https://www.huomao.com/video/v/123456",
            "https://www.huomao.tv/video/v/123456",
            "https://huomao.com/video/v/123456",
            "https://huomao.tv/video/v/123456",

            # Assert that an URL without the http(s):// prefix is correctly read.
            "www.huomao.com/123456",
            "www.huomao.tv/123456",
            "www.huomao.com/video/v/123456",
            "www.huomao.tv/video/v/123456",

            # Assert that an URL without the www prefix is correctly read.
            "huomao.com/123456",
            "huomao.tv/123456",
            "huomao.com/video/v/123456",
            "huomao.tv/video/v/123456",
        ]
        for url in should_match:
            self.assertTrue(Huomao.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            # Assert that an URL without a room_id can't be read.
            "http://www.huomao.com/",
            "http://www.huomao.tv/",
            "http://huomao.com/",
            "http://huomao.tv/",
            "https://www.huomao.com/",
            "https://www.huomao.tv/",
            "https://huomao.com/",
            "https://huomao.tv/",
            "www.huomao.com/",
            "www.huomao.tv/",
            "huomao.tv/",
            "huomao.tv/",

            # Assert that an URL without "huomao" can't be read.
            "http://www.youtube.com/123456",
            "http://www.youtube.tv/123456",
            "http://youtube.com/123456",
            "http://youtube.tv/123456",
            "https://www.youtube.com/123456",
            "https://www.youtube.tv/123456",
            "https://youtube.com/123456",
            "https://youtube.tv/123456",
        ]
        for url in should_not_match:
            self.assertFalse(Huomao.can_handle_url(url))
