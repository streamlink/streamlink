import unittest

from streamlink.plugins.ard_mediathek import ard_mediathek


class TestPluginard_mediathek(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://mediathek.daserste.de/live',
            'http://www.ardmediathek.de/tv/Sportschau/'
        ]
        for url in should_match:
            self.assertTrue(ard_mediathek.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://daserste.de/live/index.html',
            'https://www.daserste.de/live/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(ard_mediathek.can_handle_url(url))
