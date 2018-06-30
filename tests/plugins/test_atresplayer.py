import unittest

from streamlink.plugins.atresplayer import AtresPlayer


class TestPluginAtresPlayer(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.atresplayer.com/directos/antena3/',
            'http://www.atresplayer.com/directos/lasexta/',
            'https://www.atresplayer.com/directos/antena3/',
            'https://www.atresplayer.com/flooxer/programas/unas/temporada-1/dario-eme-hache-sindy-takanashi-entrevista_123/',
        ]
        for url in should_match:
            self.assertTrue(AtresPlayer.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://www.example.com/',
        ]
        for url in should_not_match:
            self.assertFalse(AtresPlayer.can_handle_url(url))
