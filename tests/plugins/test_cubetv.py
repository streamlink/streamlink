from streamlink.plugins.cubetv import CubeTV
import unittest

class TestPluginCubeTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(CubeTV.can_handle_url("https://www.cubetv.sg/Tecnosh"))
        self.assertTrue(CubeTV.can_handle_url("https://www.cubetv.sg/letsgodroid"))
        self.assertTrue(CubeTV.can_handle_url("https://www.cubetv.sg/14939646"))
        self.assertTrue(CubeTV.can_handle_url("https://www.cubetv.sg/Luladopub"))
        # shouldn't match
        self.assertFalse(CubeTV.can_handle_url("https://www.cubetv.sg/g/PUBG"))
        self.assertFalse(CubeTV.can_handle_url("https://www.cubetv.sg/c"))
        self.assertFalse(CubeTV.can_handle_url("http://www.twitch.tv/"))
        self.assertFalse(CubeTV.can_handle_url("http://www.qoo10.sg/"))
