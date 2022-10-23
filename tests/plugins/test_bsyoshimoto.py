from streamlink.plugins.bsyoshimoto import BSYoshimoto
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBSYoshimoto(PluginCanHandleUrl):
    __plugin__ = BSYoshimoto

    should_match = [
        "https://video.bsy.co.jp/",
    ]

    should_not_match = [
        "https://bsy.co.jp/",
        "https://www.bsy.co.jp/",
    ]
