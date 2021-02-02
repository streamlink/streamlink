from streamlink.plugins.nhkworld import NHKWorld
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNHKWorld(PluginCanHandleUrl):
    __plugin__ = NHKWorld

    should_match = [
        'https://www3.nhk.or.jp/nhkworld/en/live/',
    ]
