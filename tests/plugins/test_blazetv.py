from streamlink.plugins.blazetv import BlazeTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBlazeTV(PluginCanHandleUrl):
    __plugin__ = BlazeTV

    should_match_groups = [
        ("https://blaze.tv/live", {"is_live": "live"}),
        ("https://watch.blaze.tv/live/", {"is_live": "live"}),
        ("https://watch.blaze.tv/watch/replay/123456", {}),
    ]

    should_not_match = [
        "https://blaze.tv/abc",
        "https://watch.blaze.tv/watch/replay/",
        "https://watch.blaze.tv/watch/replay/abc123",
    ]
