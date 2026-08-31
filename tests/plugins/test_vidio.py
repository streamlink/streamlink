from streamlink.plugins.vidio import Vidio
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVidio(PluginCanHandleUrl):
    __plugin__ = Vidio

    should_match = [
        "https://www.vidio.com/live/6412-euronews",
        "https://www.vidio.com/live/777-metro-tv",
    ]

    should_not_match = [
        "https://www.vidio.com/",
        "https://www.vidio.com/watch/12345-asdf",
    ]
