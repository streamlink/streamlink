import unittest

from streamlink.plugins.tvnbg import TVNBG


class TestPluginTVNBG(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://tvn.bg/live/',
        ]
        for url in should_match:
            self.assertTrue(TVNBG.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(TVNBG.can_handle_url(url))
