from streamlink.plugins.nicolive import NicoLive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNicoLive(PluginCanHandleUrl):
    __plugin__ = NicoLive

    should_match = [
        "https://live2.nicovideo.jp/watch/lv534562961",
        "http://live2.nicovideo.jp/watch/lv534562961",
        "https://live.nicovideo.jp/watch/lv534562961",
        "https://live2.nicovideo.jp/watch/lv534562961?ref=rtrec&zroute=recent",
        "https://live.nicovideo.jp/watch/co2467009?ref=community",
        "https://live.nicovideo.jp/watch/co2619719",
    ]
