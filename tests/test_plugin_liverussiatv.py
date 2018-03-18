import unittest

from streamlink.plugins.live_russia_tv import LiveRussia

class TestPluginLiveRussiaTv(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(LiveRussia.can_handle_url('https://live.russia.tv/index/index/channel_id/1'))
        self.assertTrue(LiveRussia.can_handle_url('https://live.russia.tv/index/index/channel_id/199'))

        # shouldn't match
        self.assertFalse(LiveRussia.can_handle_url('https://live.russia.tv/'))
        self.assertFalse(LiveRussia.can_handle_url('http://live.russia.tv/wrongURI'))