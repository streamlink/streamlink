import unittest

from streamlink.plugins.ard_live import ard_live


class TestPluginard_live(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://daserste.de/live/index.html',
            'https://www.daserste.de/live/index.html',
        ]
        for url in should_match:
            self.assertTrue(ard_live.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://mediathek.daserste.de/live',
        ]
        for url in should_not_match:
            self.assertFalse(ard_live.can_handle_url(url))
