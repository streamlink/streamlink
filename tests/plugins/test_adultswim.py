import unittest

from streamlink.plugins.adultswim import AdultSwim


class TestPluginAdultSwim(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.adultswim.com/streams",
            "http://www.adultswim.com/streams/",
            "https://www.adultswim.com/streams/infomercials",
            "https://www.adultswim.com/streams/last-stream-on-the-left-channel/",
            "https://www.adultswim.com/videos/as-seen-on-adult-swim/wednesday-march-18th-2020",
            "https://www.adultswim.com/videos/fishcenter-live/wednesday-april-29th-2020/"
        ]
        for url in should_match:
            self.assertTrue(AdultSwim.can_handle_url(url))

        should_not_match = [
            "http://www.tvcatchup.com/",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(AdultSwim.can_handle_url(url))
