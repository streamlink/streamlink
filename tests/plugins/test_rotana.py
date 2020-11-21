import unittest

from streamlink.plugins.rotana import Rotana


class TestPluginRotana(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://rotana.net/live-classic',
            'https://rotana.net/live-music',
        ]
        for url in should_match:
            self.assertTrue(Rotana.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Rotana.can_handle_url(url), url)
