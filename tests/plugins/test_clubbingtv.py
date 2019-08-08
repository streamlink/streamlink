import unittest

from streamlink.plugins.clubbingtv import ClubbingTV


class TestPluginClubbingTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(ClubbingTV.can_handle_url("https://www.clubbingtv.com/live"))
        self.assertTrue(ClubbingTV.can_handle_url("https://www.clubbingtv.com/video/play/3950/moonlight/"))
        self.assertTrue(ClubbingTV.can_handle_url("https://www.clubbingtv.com/video/play/2897"))
        self.assertTrue(ClubbingTV.can_handle_url("https://www.clubbingtv.com/tomer-s-pick/"))

        # shouldn't match
        self.assertFalse(ClubbingTV.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(ClubbingTV.can_handle_url("http://www.youtube.com/"))
