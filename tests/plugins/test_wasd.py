import unittest

from streamlink.plugins.wasd import WASD


class TestPluginWasd(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://wasd.tv/channel',
            'https://wasd.tv/channel/',
        ]
        for url in should_match:
            self.assertTrue(WASD.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
            'https://wasd.tv/channel/12345',
            'https://wasd.tv/channel/12345/videos/67890',
            'https://wasd.tv/voodik/videos?record=123456',
        ]
        for url in should_not_match:
            self.assertFalse(WASD.can_handle_url(url), url)
