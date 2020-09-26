import unittest

from streamlink.plugins.tv999 import TV999


class TestPluginTV999(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://tv999.bg/live.html',
            'http://www.tv999.bg/live.html',
            'https://tv999.bg/live.html',
            'https://www.tv999.bg/live.html',
        ]
        for url in should_match:
            self.assertTrue(TV999.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://tv999.bg/',
            'https://tv999.bg/live',
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TV999.can_handle_url(url))
