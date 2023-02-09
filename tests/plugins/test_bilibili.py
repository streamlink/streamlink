from streamlink.plugins.bilibili import Bilibili
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBilibili(PluginCanHandleUrl):
    __plugin__ = Bilibili

    should_match = [
        "https://live.bilibili.com/123123123",
    ]
