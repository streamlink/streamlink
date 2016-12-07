import unittest

from streamlink.plugins.tvplayer import TVPlayer


class TestPluginTVPlayer(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(TVPlayer.can_handle_url("http://tvplayer.com/watch/"))
        self.assertTrue(TVPlayer.can_handle_url("http://www.tvplayer.com/watch/"))
        self.assertTrue(TVPlayer.can_handle_url("http://tvplayer.com/watch"))
        self.assertTrue(TVPlayer.can_handle_url("http://www.tvplayer.com/watch"))
        self.assertTrue(TVPlayer.can_handle_url("http://tvplayer.com/watch/dave"))
        self.assertTrue(TVPlayer.can_handle_url("http://www.tvplayer.com/watch/itv"))
        self.assertTrue(TVPlayer.can_handle_url("https://www.tvplayer.com/watch/itv"))
        self.assertTrue(TVPlayer.can_handle_url("https://tvplayer.com/watch/itv"))

        # shouldn't match
        self.assertFalse(TVPlayer.can_handle_url("http://www.tvplayer.com/"))
        self.assertFalse(TVPlayer.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(TVPlayer.can_handle_url("http://www.youtube.com/"))
