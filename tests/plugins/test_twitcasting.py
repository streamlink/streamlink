from streamlink.plugins.twitcasting import TwitCasting
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTwitCasting(PluginCanHandleUrl):
    __plugin__ = TwitCasting

    should_match = [
        "https://twitcasting.tv/twitcasting_jp",
    ]
