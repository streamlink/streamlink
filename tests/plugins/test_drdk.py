import unittest

from streamlink.plugins.drdk import DRDK


class TestPluginDRDK(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.dr.dk/drtv/kanal/dr1_20875',
            'https://www.dr.dk/drtv/kanal/dr2_20876',
            'https://www.dr.dk/drtv/kanal/dr-ramasjang_20892',
        ]
        for url in should_match:
            self.assertTrue(DRDK.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(DRDK.can_handle_url(url))
