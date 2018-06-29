import unittest

from streamlink.plugins.btv import BTV


class TestPluginBTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(BTV.can_handle_url("http://btv.bg/live"))
        self.assertTrue(BTV.can_handle_url("http://btv.bg/live/"))
        self.assertTrue(BTV.can_handle_url("http://www.btv.bg/live/"))

        # shouldn't match
        self.assertFalse(BTV.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(BTV.can_handle_url("http://www.youtube.com/"))
