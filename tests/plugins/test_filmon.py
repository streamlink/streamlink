import unittest

from streamlink.plugins.filmon import Filmon


class TestPluginFilmon(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.filmon.com/tv/bbc-news',
        ]
        for url in should_match:
            self.assertTrue(Filmon.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Filmon.can_handle_url(url))
