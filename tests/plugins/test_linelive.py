import unittest

from streamlink.plugins.linelive import LineLive


class TestPluginLineLive(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://live.line.me/channels/123/broadcast/12345678',
            'https://live.line.me/channels/123/broadcast/12345678',
        ]
        for url in should_match:
            self.assertTrue(LineLive.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
            'https://live.line.me/channels/123/upcoming/12345678',
        ]
        for url in should_not_match:
            self.assertFalse(LineLive.can_handle_url(url))
