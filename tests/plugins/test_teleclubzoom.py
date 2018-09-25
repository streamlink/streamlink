import unittest

from streamlink.plugins.teleclubzoom import TeleclubZoom


class TestPluginTeleclubZoom(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.teleclubzoom.ch',
            'https://www.teleclubzoom.ch/',
        ]
        for url in should_match:
            self.assertTrue(TeleclubZoom.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TeleclubZoom.can_handle_url(url))
