from streamlink.plugins.useetv import UseeTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlUseeTV(PluginCanHandleUrl):
    __plugin__ = UseeTV

    should_match = [
        "http://useetv.com/any",
        "http://useetv.com/any/path",
        "http://www.useetv.com/any",
        "http://www.useetv.com/any/path",
        "https://useetv.com/any",
        "https://useetv.com/any/path",
        "https://www.useetv.com/any",
        "https://www.useetv.com/any/path",
    ]
