import unittest

from streamlink.plugins.drdk import DRDK


class TestPluginDRDK(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.dr.dk/tv/live/dr1',
            'https://www.dr.dk/tv/live/dr2',
            'https://www.dr.dk/tv/se/matador/matador-saeson-3/matador-15-24',
        ]
        for url in should_match:
            self.assertTrue(DRDK.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(DRDK.can_handle_url(url))
