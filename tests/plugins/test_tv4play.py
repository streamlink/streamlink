import unittest

from streamlink.plugins.tv4play import TV4Play


class TestPluginTV4Play(unittest.TestCase):

    def test_can_handle_url(self):
        should_match = [
            'https://www.tv4play.se/program/fridas-vm-resa/10000884',
            'https://www.tv4play.se/program/monk/3938989',
            'https://www.tv4play.se/program/nyheterna/10378590',
            'https://www.fotbollskanalen.se/video/10395484/ghoddos-fullbordar-vandningen---ger-ofk-ledningen/',
        ]
        for url in should_match:
            self.assertTrue(TV4Play.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TV4Play.can_handle_url(url))
