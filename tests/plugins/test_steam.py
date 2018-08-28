import unittest

from streamlink.plugins.steam import SteamBroadcastPlugin


class TestPluginSteamBroadcastPlugin(unittest.TestCase):
    def test_can_handle_url(self):
        self.assertTrue(SteamBroadcastPlugin.can_handle_url('https://steamcommunity.com/broadcast/watch/12432432'))
        self.assertTrue(SteamBroadcastPlugin.can_handle_url('http://steamcommunity.com/broadcast/watch/342342'))
        self.assertTrue(SteamBroadcastPlugin.can_handle_url('https://steam.tv/dota2'))
        self.assertTrue(SteamBroadcastPlugin.can_handle_url('http://steam.tv/dota2'))

    def test_can_handle_url_negative(self):
        # shouldn't match
        self.assertFalse(SteamBroadcastPlugin.can_handle_url('http://steamcommunity.com/broadcast'))
        self.assertFalse(SteamBroadcastPlugin.can_handle_url('https://steamcommunity.com'))
        self.assertFalse(SteamBroadcastPlugin.can_handle_url('https://youtube.com'))
