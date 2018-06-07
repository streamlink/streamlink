import unittest

from streamlink.plugins.ustvnow import USTVNow


class TestPluginUSTVNow(unittest.TestCase):
    def test_can_handle_url(self):
        self.assertTrue(USTVNow.can_handle_url("http://watch.ustvnow.com"))
        self.assertTrue(USTVNow.can_handle_url("https://watch.ustvnow.com/"))
        self.assertTrue(USTVNow.can_handle_url("http://watch.ustvnow.com/watch"))
        self.assertTrue(USTVNow.can_handle_url("https://watch.ustvnow.com/watch"))
        self.assertTrue(USTVNow.can_handle_url("https://watch.ustvnow.com/watch/syfy"))
        self.assertTrue(USTVNow.can_handle_url("https://watch.ustvnow.com/guide/foxnews"))

    def test_can_not_handle_url(self):
        self.assertFalse(USTVNow.can_handle_url("http://www.tvplayer.com"))
