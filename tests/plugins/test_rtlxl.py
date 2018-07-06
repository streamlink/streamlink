import unittest

from streamlink.plugins.rtlxl import rtlxl


class TestPluginrtlxl(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.rtl.nl/video/206a0db0-9bc8-3a32-bda3-e9b3a9d4d377/',
        ]
        for url in should_match:
            self.assertTrue(rtlxl.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.rtl.nl/',
        ]
        for url in should_not_match:
            self.assertFalse(rtlxl.can_handle_url(url))
