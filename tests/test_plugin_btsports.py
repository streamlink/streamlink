import unittest

from streamlink.plugins.btsports import BTSports


class TestPluginBTSports(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(BTSports.can_handle_url("https://sport.bt.com/btsportsplayer/football-match-1"))
        self.assertTrue(BTSports.can_handle_url("https://sport.bt.com/ss/Satellite/btsportsplayer/football-match-1"))

        # shouldn't match
        self.assertFalse(BTSports.can_handle_url("http://www.bt.com/"))
        self.assertFalse(BTSports.can_handle_url("http://bt.com/"))
        self.assertFalse(BTSports.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(BTSports.can_handle_url("http://www.youtube.com/"))
