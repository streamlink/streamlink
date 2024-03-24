from streamlink.plugins.bilibili import Bilibili
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBilibili(PluginCanHandleUrl):
    __plugin__ = Bilibili

    should_match_groups = [
        ("https://live.bilibili.com/CHANNEL", {"channel": "CHANNEL"}),
    ]
