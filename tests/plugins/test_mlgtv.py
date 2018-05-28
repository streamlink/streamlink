import unittest

from streamlink.plugins.mlgtv import MLGTV


class TestPluginMLGTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://tv.majorleaguegaming.com/channel/call-of-duty-german",
            "http://eve.majorleaguegaming.com/overwatch",
            "http://eve.majorleaguegaming.com/starcraft",
            "http://player2.majorleaguegaming.com/api/v2/player/embed/live/?ch=call-of-duty"
        ]
        for url in should_match:
            self.assertTrue(MLGTV.can_handle_url(url))

        should_not_match = [
            "http://www.mlg.com/"
        ]
        for url in should_not_match:
            self.assertFalse(MLGTV.can_handle_url(url))
