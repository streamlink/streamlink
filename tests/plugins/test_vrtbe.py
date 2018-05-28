import unittest

from streamlink.plugins.vrtbe import VRTbe


class TestPluginVRTbe(unittest.TestCase):
    def test_can_handle_url(self):
        # LIVE
        self.assertTrue(VRTbe.can_handle_url("https://www.vrt.be/vrtnu/kanalen/canvas/"))
        self.assertTrue(VRTbe.can_handle_url("https://www.vrt.be/vrtnu/kanalen/een/"))
        self.assertTrue(VRTbe.can_handle_url("https://www.vrt.be/vrtnu/kanalen/ketnet/"))

        # VOD
        self.assertTrue(VRTbe.can_handle_url("https://www.vrt.be/vrtnu/a-z/belfast-zoo/1/belfast-zoo-s1a14/"))
        self.assertTrue(VRTbe.can_handle_url("https://www.vrt.be/vrtnu/a-z/sporza--korfbal/2017/sporza--korfbal-s2017-sporza-korfbal/"))
        self.assertTrue(VRTbe.can_handle_url("https://www.vrt.be/vrtnu/a-z/de-grote-peter-van-de-veire-ochtendshow/2017/de-grote-peter-van-de-veire-ochtendshow-s2017--en-parels-voor-de-zwijnen-ook/"))

        # shouldn't match
        self.assertFalse(VRTbe.can_handle_url("https://example.com/"))
        self.assertFalse(VRTbe.can_handle_url("http://www.local.local/"))
