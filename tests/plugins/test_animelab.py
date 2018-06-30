import unittest

from streamlink.plugins.animelab import AnimeLab


class TestPluginAnimeLab(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.animelab.com/player/123',
            'https://animelab.com/player/123',
        ]
        for url in should_match:
            self.assertTrue(AnimeLab.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(AnimeLab.can_handle_url(url))
