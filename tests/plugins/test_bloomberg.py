import unittest

from streamlink.plugins.bloomberg import Bloomberg


class TestPluginBloomberg(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://www.bloomberg.com/live/us",
            "https://www.bloomberg.com/live/europe",
            "https://www.bloomberg.com/live/asia",
            "https://www.bloomberg.com/live/stream",
            "https://www.bloomberg.com/live/emea",
            "https://www.bloomberg.com/live/asia_stream",
            "https://www.bloomberg.com/news/videos/2017-04-17/wozniak-science-fiction-finally-becoming-reality-video",
            "http://www.bloomberg.com/news/videos/2017-04-17/russia-s-stake-in-a-u-s-north-korea-conflict-video"
        ]
        for url in should_match:
            self.assertTrue(Bloomberg.can_handle_url(url))

        should_not_match = [
            "https://www.bloomberg.com/live/",
            "https://www.bloomberg.com/politics/articles/2017-04-17/french-race-up-for-grabs-days-before-voters-cast"
            + "-first-ballots",
            "http://www.tvcatchup.com/",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(Bloomberg.can_handle_url(url))
