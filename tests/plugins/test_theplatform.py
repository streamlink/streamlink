import unittest

from streamlink.plugins.theplatform import ThePlatform


class TestPluginThePlatform(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://player.theplatform.com/p/',
            'http://player.theplatform.com/p/',
        ]
        for url in should_match:
            self.assertTrue(ThePlatform.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(ThePlatform.can_handle_url(url))
