import unittest

from streamlink.plugins.adultswim import AdultSwim


class TestPluginAdultSwim(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(AdultSwim.can_handle_url("http://www.adultswim.com/videos/streams/toonami"))
        self.assertTrue(AdultSwim.can_handle_url("http://www.adultswim.com/videos/streams/"))
        self.assertTrue(AdultSwim.can_handle_url("http://www.adultswim.com/videos/streams/last-stream-on-the-left"))
        self.assertTrue(AdultSwim.can_handle_url("http://www.adultswim.com/videos/specials/the-adult-swim-golf-classic-extended/"))

        # shouldn't match
        self.assertFalse(AdultSwim.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(AdultSwim.can_handle_url("http://www.youtube.com/"))
