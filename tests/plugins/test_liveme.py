import unittest

from streamlink.plugins.liveme import LiveMe


class TestPluginLiveMe(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.liveme.com/live.html?videoid=12312312312312312312",
            "http://www.liveme.com/live.html?videoid=23123123123123123123&countryCode=undefined"
        ]
        for url in should_match:
            self.assertTrue(LiveMe.can_handle_url(url))

        should_not_match = [
            "http://www.liveme.com/",
            "http://www.liveme.com/explore.html",
            "http://www.liveme.com/media/play"
        ]
        for url in should_not_match:
            self.assertFalse(LiveMe.can_handle_url(url))
