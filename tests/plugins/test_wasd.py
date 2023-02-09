from streamlink.plugins.wasd import WASD
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlWasd(PluginCanHandleUrl):
    __plugin__ = WASD

    should_match = [
        "https://wasd.tv/channel",
        "https://wasd.tv/channel/",
    ]

    should_not_match = [
        "https://wasd.tv/channel/12345",
        "https://wasd.tv/channel/12345/videos/67890",
        "https://wasd.tv/voodik/videos?record=123456",
    ]
