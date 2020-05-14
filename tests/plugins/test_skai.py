import unittest

from streamlink.plugins.skai import Skai


class TestPluginSkai(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.skai.gr/player/tvlive/',
            'http://www.skaitv.gr/live',
        ]
        for url in should_match:
            self.assertTrue(Skai.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Skai.can_handle_url(url))
