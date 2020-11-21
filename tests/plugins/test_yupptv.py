import unittest

from streamlink.plugins.yupptv import YuppTV


class TestPluginYuppTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.yupptv.com/channels/etv-telugu/live',
            'https://www.yupptv.com/channels/india-today-news/news/25326023/15-jun-2018',
        ]
        for url in should_match:
            self.assertTrue(YuppTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://ewe.de',
            'https://netcologne.de',
            'https://zattoo.com',
        ]
        for url in should_not_match:
            self.assertFalse(YuppTV.can_handle_url(url))
