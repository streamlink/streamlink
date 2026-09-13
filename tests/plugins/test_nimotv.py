from streamlink.plugins.nimotv import NimoTV
from tests.plugins import PluginCanHandleUrl


class TestPluginNimoTV(PluginCanHandleUrl):
    __plugin__ = NimoTV

    should_match = [
        "https://m.nimo.tv/CHANNEL",
        "https://www.nimo.tv/CHANNEL?foo",
        "https://m.nimo.tv/live/CHANNELID/",
        "https://www.nimo.tv/live/CHANNELID#bar",
    ]

    should_not_match = [
        "https://www.nimo.tv/",
        "https://m.nimo.tv/",
    ]
