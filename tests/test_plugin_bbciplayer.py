import unittest

from streamlink.plugins.bbciplayer import BBCiPlayer


class TestPluginBBCiPlayer(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(BBCiPlayer.can_handle_url("http://www.bbc.co.uk/iplayer/episode/b00ymh67/madagascar-1-island-of-marvels"))
        self.assertTrue(BBCiPlayer.can_handle_url("http://www.bbc.co.uk/iplayer/live/bbcone"))

        # shouldn't match
        self.assertFalse(BBCiPlayer.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(BBCiPlayer.can_handle_url("http://www.sportal.bg/sportal_live_tv.php?str=15"))
        self.assertFalse(BBCiPlayer.can_handle_url("http://www.bbc.co.uk/iplayer/"))

    def test_vpid_hash(self):
        self.assertEqual(
            "71c345435589c6ddeea70d6f252e2a52281ecbf3",
            BBCiPlayer._hash_vpid("1234567890")
        )
