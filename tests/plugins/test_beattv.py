import unittest

from streamlink.plugins.beattv import BeatTV


class TestPluginBeatTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://be-at.tv/',
        ]
        for url in should_match:
            self.assertTrue(BeatTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(BeatTV.can_handle_url(url))
