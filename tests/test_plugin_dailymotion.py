import unittest

from streamlink.plugins.dailymotion import DailyMotion


class TestPluginDailyMotion(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(DailyMotion.can_handle_url("https://www.dailymotion.com/video/xigbvx"))
        self.assertTrue(DailyMotion.can_handle_url("https://www.dailymotion.com/france24"))
        self.assertTrue(DailyMotion.can_handle_url("https://www.dailymotion.com/embed/video/xigbvx"))

        # shouldn't match
        self.assertFalse(DailyMotion.can_handle_url("https://www.dailymotion.com/"))
        self.assertFalse(DailyMotion.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(DailyMotion.can_handle_url("http://www.youtube.com/"))
