import unittest

from streamlink.plugins.douyutv import Douyutv


class TestPluginDouyutv(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.douyu.com/123123123',
            'https://v.douyu.com/show/ABC123123123ABC',
        ]
        for url in should_match:
            self.assertTrue(Douyutv.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Douyutv.can_handle_url(url))
