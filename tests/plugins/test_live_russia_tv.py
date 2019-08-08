import unittest

from streamlink.plugins.live_russia_tv import LiveRussia


class TestPluginLiveRussiaTv(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(LiveRussia.can_handle_url('https://live.russia.tv/channel/1'))
        self.assertTrue(LiveRussia.can_handle_url('https://live.russia.tv/channel/199'))
        self.assertTrue(LiveRussia.can_handle_url('https://live.russia.tv/'))
        self.assertTrue(LiveRussia.can_handle_url('https://live.russia.tv/video/show/brand_id/60473/episode_id/2187772/video_id/2204594'))

    def test_can_handle_url_negative(self):
        self.assertFalse(LiveRussia.can_handle_url('http://live.france.tv/somethingelse'))
        self.assertFalse(LiveRussia.can_handle_url('https://youtube.com/watch?v=4567uj'))
