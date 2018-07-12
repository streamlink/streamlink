import unittest
from streamlink.plugins.kingkong import Kingkong


class TestPluginKingkong(unittest.TestCase):
    def test_can_handle_url(self):
        # Valid stream and VOD URLS
        self.assertTrue(Kingkong.can_handle_url(
            "https://www.kingkong.com.tw/600000"))
        self.assertTrue(Kingkong.can_handle_url(
            "https://www.kingkong.com.tw/video/2152350G38400MJTU"))

        # Others
        self.assertFalse(Kingkong.can_handle_url(
            "https://www.kingkong.com.tw/category/lol"))
        self.assertFalse(Kingkong.can_handle_url(
            "https://www.kingkong.com.tw/videos/2152350"))
