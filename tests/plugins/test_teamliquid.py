import unittest

from streamlink.plugins.teamliquid import Teamliquid


class TestPluginTeamliquid(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Teamliquid.can_handle_url("http://www.teamliquid.net/video/streams/Classic%20BW%20VODs"))
        self.assertTrue(Teamliquid.can_handle_url("http://teamliquid.net/video/streams/iwl-fuNny"))
        self.assertTrue(Teamliquid.can_handle_url("http://www.teamliquid.net/video/streams/OGamingTV%20SC2"))
        self.assertTrue(Teamliquid.can_handle_url("http://www.teamliquid.net/video/streams/Check"))
        self.assertTrue(Teamliquid.can_handle_url("https://tl.net/video/streams/GSL"))

        # shouldn't match
        self.assertFalse(Teamliquid.can_handle_url("http://www.teamliquid.net/Classic%20BW%20VODs"))
        self.assertFalse(Teamliquid.can_handle_url("http://www.teamliquid.net/video/Check"))
        self.assertFalse(Teamliquid.can_handle_url("http://www.teamliquid.com/video/streams/Check"))
        self.assertFalse(Teamliquid.can_handle_url("http://www.teamliquid.net/video/stream/Check"))
