import unittest

from streamlink.plugins.dingittv import DingitTV


class TestPluginDingitTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.dingit.tv/highlight/123123123',
        ]
        for url in should_match:
            self.assertTrue(DingitTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(DingitTV.can_handle_url(url))
