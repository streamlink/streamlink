import unittest

from streamlink.plugins.weeb import Weeb


class TestPluginWeeb(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://weeb.tv/channel/example',
        ]
        for url in should_match:
            self.assertTrue(Weeb.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Weeb.can_handle_url(url))
