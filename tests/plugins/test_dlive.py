from streamlink.plugins.dlive import DLive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDLive(PluginCanHandleUrl):
    __plugin__ = DLive

    should_match = [
        "https://dlive.tv/pewdiepie",
        "https://dlive.tv/p/pdp+K6DqqtYWR",
    ]

    should_not_match = [
        "https://dlive.tv/",
    ]
