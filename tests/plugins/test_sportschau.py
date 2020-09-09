import unittest

from streamlink.plugins.sportschau import Sportschau


class TestPluginSportschau(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.sportschau.de/wintersport/videostream-livestream---wintersport-im-ersten-242.html',
            'https://www.sportschau.de/weitere/allgemein/video-kite-surf-world-tour-100.html',
        ]
        for url in should_match:
            self.assertTrue(Sportschau.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Sportschau.can_handle_url(url))
