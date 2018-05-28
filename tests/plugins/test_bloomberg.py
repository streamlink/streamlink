import unittest

from streamlink.plugins.bloomberg import Bloomberg


class TestPluginBloomberg(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Bloomberg.can_handle_url("https://www.bloomberg.com/live/us"))
        self.assertTrue(Bloomberg.can_handle_url("https://www.bloomberg.com/live/europe"))
        self.assertTrue(Bloomberg.can_handle_url("https://www.bloomberg.com/live/asia"))
        self.assertTrue(Bloomberg.can_handle_url("https://www.bloomberg.com/live/stream"))
        self.assertTrue(Bloomberg.can_handle_url("https://www.bloomberg.com/live/emea"))
        self.assertTrue(Bloomberg.can_handle_url("https://www.bloomberg.com/live/asia_stream"))
        self.assertTrue(Bloomberg.can_handle_url("https://www.bloomberg.com/news/videos/2017-04-17/wozniak-science-fiction-finally-becoming-reality-video"))
        self.assertTrue(Bloomberg.can_handle_url("http://www.bloomberg.com/news/videos/2017-04-17/russia-s-stake-in-a-u-s-north-korea-conflict-video"))

        # shouldn't match
        self.assertFalse(Bloomberg.can_handle_url("https://www.bloomberg.com/live/"))
        self.assertFalse(Bloomberg.can_handle_url("https://www.bloomberg.com/politics/articles/2017-04-17/french-race-up-for-grabs-days-before-voters-cast-first-ballots"))
        self.assertFalse(Bloomberg.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Bloomberg.can_handle_url("http://www.youtube.com/"))
