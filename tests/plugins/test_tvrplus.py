from streamlink.plugins.tvrplus import TVRPlus
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVRPlus(PluginCanHandleUrl):
    __plugin__ = TVRPlus

    should_match = [
        "https://tvrplus.ro",
        "https://tvrplus.ro/",
        "https://tvrplus.ro/live/tvr-1",
        "https://www.tvrplus.ro",
        "https://www.tvrplus.ro/",
        "https://www.tvrplus.ro/live/tvr-1",
        "https://www.tvrplus.ro/live/tvr-3",
        "https://www.tvrplus.ro/live/tvr-international",
    ]

    should_not_match = [
        "https://www.tvrplus.ro/emisiuni",
    ]
