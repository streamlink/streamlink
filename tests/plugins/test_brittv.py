import unittest

from streamlink.plugins.brittv import BritTV


class TestPluginBritTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://brittv.co.uk/watch/?channel=1',
        ]
        for url in should_match:
            self.assertTrue(BritTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(BritTV.can_handle_url(url))
