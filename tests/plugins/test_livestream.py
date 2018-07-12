import unittest

from streamlink.plugins.livestream import Livestream


class TestPluginLivestream(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://livestream.com/',
            'https://www.livestream.com/',
        ]
        for url in should_match:
            self.assertTrue(Livestream.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Livestream.can_handle_url(url))
