import unittest

from streamlink.plugins.dplay import Dplay


class TestPluginDplay(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.dplay.dk/videoer/studie-5/season-2-episode-1',
            'https://www.dplay.no/videoer/danskebaten/sesong-1-episode-1',
            'https://www.dplay.se/videos/breaking-news/breaking-news-med-filip-fredrik-750',
        ]
        for url in should_match:
            self.assertTrue(Dplay.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Dplay.can_handle_url(url))
