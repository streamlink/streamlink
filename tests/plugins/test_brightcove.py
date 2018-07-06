import unittest

from streamlink.plugins.brightcove import Brightcove


class TestPluginBrightcove(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://players.brightcove.net/123/default_default/index.html?videoId=456',
            'http://players.brightcove.net/456/default_default/index.html?videoId=789',
        ]
        for url in should_match:
            self.assertTrue(Brightcove.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Brightcove.can_handle_url(url))
