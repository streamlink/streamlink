import unittest

from streamlink.plugins.live_russia_tv import LiveRussia


class TestPluginLiveRussiaTv(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://live.russia.tv/channel/1",
            "https://live.russia.tv/channel/199",
            "https://live.russia.tv/",
            "https://live.russia.tv/video/show/brand_id/60473/episode_id/2187772/video_id/2204594"
        ]
        for url in should_match:
            self.assertTrue(LiveRussia.can_handle_url(url))

        should_not_match = [
            "http://live.france.tv/somethingelse",
            "https://youtube.com/watch?v=4567uj"
        ]
        for url in should_not_match:
            self.assertFalse(LiveRussia.can_handle_url(url))
