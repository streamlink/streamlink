import unittest

from streamlink.plugins.tvrplus import TVRPlus


class TestPluginTVRPlus(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://tvrplus.ro/live/tvr-1",
            "http://www.tvrplus.ro/live/tvr-1",
            "http://www.tvrplus.ro/live/tvr-3",
            "http://www.tvrplus.ro/live/tvr-international",
        ]
        for url in should_match:
            self.assertTrue(TVRPlus.can_handle_url(url))

        should_not_match = [
            "http://www.tvrplus.ro/",
        ]
        for url in should_not_match:
            self.assertFalse(TVRPlus.can_handle_url(url))
