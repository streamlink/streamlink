import unittest

from streamlink.plugins.seetv import SeeTV


class TestPluginSeeTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://seetv.tv/vse-tv-online/example',
        ]
        for url in should_match:
            self.assertTrue(SeeTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(SeeTV.can_handle_url(url))
