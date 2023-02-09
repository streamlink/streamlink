from streamlink.plugins.app17 import App17
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlApp17(PluginCanHandleUrl):
    __plugin__ = App17

    should_match = [
        "https://17.live/en-US/live/123123",
        "https://17.live/en/live/123123",
        "https://17.live/ja/live/123123",
    ]
