from streamlink.plugins.brightcove import Brightcove
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBrightcove(PluginCanHandleUrl):
    __plugin__ = Brightcove

    should_match = [
        "https://players.brightcove.net/123/default_default/index.html?videoId=456",
        "https://players.brightcove.net/456/default_default/index.html?videoId=789",
    ]
