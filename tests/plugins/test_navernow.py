import unittest

from streamlink.plugins.navernow import NaverNow


class TestPluginNaverNow(unittest.TestCase):

    def test_can_handle_url(self):
        should_match = [
            "https://now.naver.com/705",
            "https://now.naver.com/680",
            "https://now.naver.com/719?airbridge_referrer=airbridge" # url with parameter
        ]
        for url in should_match:
            self.assertTrue(NaverNow.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            "https://now.naver.com/about",
            "https://example.com/index.html"
        ]
        for url in should_not_match:
            self.assertFalse(NaverNow.can_handle_url(url))
