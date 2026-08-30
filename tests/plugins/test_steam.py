from streamlink.plugins.steam import SteamBroadcastPlugin
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSteamBroadcastPlugin(PluginCanHandleUrl):
    __plugin__ = SteamBroadcastPlugin

    should_match = [
        "https://steamcommunity.com/broadcast/watch/12432432",
        "http://steamcommunity.com/broadcast/watch/342342",
        "https://steam.tv/dota2",
        "http://steam.tv/dota2",
    ]

    should_not_match = [
        "http://steamcommunity.com/broadcast",
        "https://steamcommunity.com",
    ]
