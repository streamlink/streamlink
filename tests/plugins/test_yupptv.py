import unittest

from streamlink.plugins.yupptv import YuppTV


class TestPluginZattoo(unittest.TestCase):
    def test_can_handle_url(self):
        self.assertTrue(YuppTV.can_handle_url('https://www.yupptv.com/channels/etv-telugu/live'))
        self.assertTrue(YuppTV.can_handle_url('https://www.yupptv.com/channels/india-today-news/news/25326023/15-jun-2018'))

    def test_can_handle_negative(self):
        # shouldn't match
        self.assertFalse(YuppTV.can_handle_url('https://ewe.de'))
        self.assertFalse(YuppTV.can_handle_url('https://netcologne.de'))
        self.assertFalse(YuppTV.can_handle_url('https://zattoo.com'))
