from streamlink.plugins.cubetv import CubeTV
import unittest


class TestPluginCubeTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(CubeTV.can_handle_url("https://www.cube.tv/Tecnosh"))
        self.assertTrue(CubeTV.can_handle_url("https://www.cube.tv/garotadoblog"))
        self.assertTrue(CubeTV.can_handle_url("https://www.cube.tv/demi"))
        self.assertTrue(CubeTV.can_handle_url("https://www.cube.tv/Luladopub"))
        # shouldn't match
        self.assertFalse(CubeTV.can_handle_url("https://www.cubetv.sg/g/PUBG"))
        self.assertFalse(CubeTV.can_handle_url("https://www.cubetv.sg/c"))
        self.assertFalse(CubeTV.can_handle_url("http://www.twitch.tv/"))
        self.assertFalse(CubeTV.can_handle_url("http://www.qoo10.sg/"))
