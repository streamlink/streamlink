import unittest

from streamlink.plugins.npo import NPO


class TestPluginNPO(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.npo.nl/live/npo-1',
            'https://www.npo.nl/live/npo-2',
            'https://www.npo.nl/live/npo-zapp',
            'https://www.zapp.nl/tv-kijken',
            'https://zappelin.nl/schatkist/videos/VPWON_1284504',
        ]
        for url in should_match:
            self.assertTrue(NPO.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(NPO.can_handle_url(url))
