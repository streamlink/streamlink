import unittest

from streamlink.plugins.piczel import Piczel


class TestPluginPiczel(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://piczel.tv/watch/example',
        ]
        for url in should_match:
            self.assertTrue(Piczel.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Piczel.can_handle_url(url))
