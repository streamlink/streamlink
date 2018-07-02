import unittest

from streamlink.plugins.live_russia_tv import LiveRussia


class TestPluginLiveRussiaTv(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(LiveRussia.can_handle_url('https://live.russia.tv/index/index/channel_id/1'))
        self.assertTrue(LiveRussia.can_handle_url('https://live.russia.tv/index/index/channel_id/199'))
        self.assertTrue(LiveRussia.can_handle_url('https://live.russia.tv/'))
        self.assertTrue(LiveRussia.can_handle_url('http://live.russia.tv/somethingelse'))
        self.assertTrue(LiveRussia.can_handle_url('https://russia.tv/fifaworldcup/games/1832668/video/1800840'))

    def test_can_handle_url_negative(self):
        self.assertFalse(LiveRussia.can_handle_url('http://live.france.tv/somethingelse'))
        self.assertFalse(LiveRussia.can_handle_url('https://youtube.com/watch?v=4567uj'))
