import unittest

from streamlink.plugins.tvcatchup import TVCatchup


class TestPluginTVCatchup(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(TVCatchup.can_handle_url("http://tvcatchup.com/watch/bbcone"))
        self.assertTrue(TVCatchup.can_handle_url("http://www.tvcatchup.com/watch/five"))
        self.assertTrue(TVCatchup.can_handle_url("https://www.tvcatchup.com/watch/bbctwo"))

        # shouldn't match
        self.assertFalse(TVCatchup.can_handle_url("http://www.tvplayer.com/"))
        self.assertFalse(TVCatchup.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(TVCatchup.can_handle_url("http://www.youtube.com/"))