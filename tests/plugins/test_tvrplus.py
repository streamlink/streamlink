from streamlink.plugins.tvrplus import TVRPlus
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVRPlus(PluginCanHandleUrl):
    __plugin__ = TVRPlus

    should_match = [
        "http://tvrplus.ro/live/tvr-1",
        "http://www.tvrplus.ro/live/tvr-1",
        "http://www.tvrplus.ro/live/tvr-3",
        "http://www.tvrplus.ro/live/tvr-international",
    ]

    should_not_match = [
        "http://www.tvrplus.ro/",
    ]
