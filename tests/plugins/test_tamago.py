import unittest

from streamlink.plugins.tamago import Tamago


class TestPluginTamago(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://player.tamago.live/w/2009642',
            'https://player.tamago.live/w/1882066',
            'https://player.tamago.live/w/1870142',
            'https://player.tamago.live/w/1729968',
        ]
        for url in should_match:
            self.assertTrue(Tamago.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://download.tamago.live/faq',
            'https://player.tamago.live/gaming/pubg',
            'https://www.twitch.tv/twitch'
        ]
        for url in should_not_match:
            self.assertFalse(Tamago.can_handle_url(url))
