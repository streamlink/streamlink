from streamlink.plugins.linelive import LineLive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLineLive(PluginCanHandleUrl):
    __plugin__ = LineLive

    should_match_groups = [
        ("https://live.line.me/channels/123/broadcast/456", {"channel": "123", "broadcast": "456"}),
    ]

    should_not_match = [
        "https://live.line.me/",
        "https://live.line.me/channels/123/",
        "https://live.line.me/channels/123/upcoming/456",
    ]
