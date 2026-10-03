from streamlink.plugins.blazetv import BlazeTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBlazeTV(PluginCanHandleUrl):
    __plugin__ = BlazeTV

    should_match_groups = [
        (
            "https://blaze.tv/live",
            {"is_live": "live"},
        ),
        (
            "https://www.blaze.tv/live",
            {"is_live": "live"},
        ),
        (
            "https://watch.blaze.tv/live",
            {"is_live": "live"},
        ),
        (
            "https://www.blaze.tv/watch/replay/12345",
            {},
        ),
    ]

    should_not_match = [
        "https://blaze.tv/",
        "https://www.blaze.tv/",
        "https://www.blaze.tv/watch",
    ]
