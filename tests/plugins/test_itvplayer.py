import unittest

from streamlink.plugins.itvplayer import ITVPlayer


class TestPluginITVPlayer(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.itv.com/hub/itv',
            'https://www.itv.com/hub/itv2',
        ]
        for url in should_match:
            self.assertTrue(ITVPlayer.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(ITVPlayer.can_handle_url(url))
