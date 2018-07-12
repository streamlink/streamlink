import unittest

from streamlink.plugins.huajiao import Huajiao


class TestPluginHuajiao(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.huajiao.com/l/123123123',
        ]
        for url in should_match:
            self.assertTrue(Huajiao.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Huajiao.can_handle_url(url))
