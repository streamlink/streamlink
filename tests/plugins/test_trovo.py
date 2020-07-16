import unittest

from streamlink.plugins.trovo import Trovo


class TestPluginTrovo(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://trovo.live/Ler_GG',
            'http://trovo.live/Ler_GG'
        ]
        for url in should_match:
            self.assertTrue(Trovo.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.dummywebsite.com/',
            'http://www.trovo.com/'
        ]
        for url in should_not_match:
            self.assertFalse(Trovo.can_handle_url(url))
