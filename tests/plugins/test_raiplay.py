import unittest

from streamlink.plugins.raiplay import RaiPlay


class TestPluginRaiPlay(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(RaiPlay.can_handle_url("http://www.raiplay.it/dirette/rai1"))
        self.assertTrue(RaiPlay.can_handle_url("http://www.raiplay.it/dirette/rai2"))
        self.assertTrue(RaiPlay.can_handle_url("http://www.raiplay.it/dirette/rai3"))
        self.assertTrue(RaiPlay.can_handle_url("http://raiplay.it/dirette/rai3"))
        self.assertTrue(RaiPlay.can_handle_url("https://raiplay.it/dirette/rai3"))
        self.assertTrue(RaiPlay.can_handle_url("http://www.raiplay.it/dirette/rainews24"))
        self.assertTrue(RaiPlay.can_handle_url("https://www.raiplay.it/dirette/rainews24"))

        # shouldn't match
        self.assertFalse(RaiPlay.can_handle_url("http://www.adultswim.com/videos/streams/toonami"))
        self.assertFalse(RaiPlay.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(RaiPlay.can_handle_url("http://www.youtube.com/"))
