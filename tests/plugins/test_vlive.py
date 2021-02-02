from streamlink.plugins.vlive import Vlive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVlive(PluginCanHandleUrl):
    __plugin__ = Vlive

    should_match = [
        "https://www.vlive.tv/video/156824",
        "https://www.vlive.tv/post/0-19740901"
    ]

    should_not_match = [
        "https://www.vlive.tv/events/2019vheartbeat?lang=en",
    ]
