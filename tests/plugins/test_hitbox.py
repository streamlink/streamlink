import unittest

from streamlink.plugins.hitbox import Hitbox


class TestPluginHitbox(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.smashcast.tv/pixelradio',
            'https://www.hitbox.tv/pixelradio',
            'https://www.smashcast.tv/jurnalfm',
            'https://www.smashcast.tv/sscaitournament',
        ]
        for url in should_match:
            self.assertTrue(Hitbox.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Hitbox.can_handle_url(url))
