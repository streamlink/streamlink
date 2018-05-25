import unittest

from streamlink.plugins.goltelevision import GOLTelevision


class TestPluginEuronews(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(GOLTelevision.can_handle_url("http://www.goltelevision.com/live"))
        self.assertTrue(GOLTelevision.can_handle_url("http://goltelevision.com/live"))
        self.assertTrue(GOLTelevision.can_handle_url("https://goltelevision.com/live"))
        self.assertTrue(GOLTelevision.can_handle_url("https://www.goltelevision.com/live"))

        # shouldn't match
        self.assertFalse(GOLTelevision.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(GOLTelevision.can_handle_url("http://www.youtube.com/"))
