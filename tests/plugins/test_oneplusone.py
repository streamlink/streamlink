from streamlink.plugins.oneplusone import OnePlusOne
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOnePlusOne(PluginCanHandleUrl):
    __plugin__ = OnePlusOne

    should_match = [
        "https://1plus1.video/ru/tvguide/plusplus/online",
        "https://1plus1.video/tvguide/1plus1/online",
        "https://1plus1.video/tvguide/2plus2/online",
        "https://1plus1.video/tvguide/bigudi/online",
        "https://1plus1.video/tvguide/plusplus/online",
        "https://1plus1.video/tvguide/sport/online",
        "https://1plus1.video/tvguide/tet/online",
        "https://1plus1.video/tvguide/uniantv/online",
    ]

    should_not_match = [
        "https://1plus1.video/",
    ]
