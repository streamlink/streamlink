import unittest

from streamlink.plugins.twitcasting import TwitCasting


class TestPluginTwitCasting(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://twitcasting.tv/c:kk1992kkkk',
            'https://twitcasting.tv/icchy8591/movie/566593738',
        ]
        for url in should_match:
            self.assertTrue(TwitCasting.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TwitCasting.can_handle_url(url))
