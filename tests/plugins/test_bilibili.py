import unittest

from streamlink.plugins.bilibili import Bilibili


class TestPluginBilibili(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://live.bilibili.com/123123123',
        ]
        for url in should_match:
            self.assertTrue(Bilibili.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Bilibili.can_handle_url(url))
