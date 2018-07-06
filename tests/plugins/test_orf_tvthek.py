import unittest

from streamlink.plugins.orf_tvthek import ORFTVThek


class TestPluginORFTVThek(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://tvthek.orf.at/live/Wetter/13953206',
        ]
        for url in should_match:
            self.assertTrue(ORFTVThek.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(ORFTVThek.can_handle_url(url))
