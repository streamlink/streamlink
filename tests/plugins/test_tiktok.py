from streamlink.plugins.tiktok import TikTok
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTikTok(PluginCanHandleUrl):
    __plugin__ = TikTok

    should_match_groups = [
        ("https://www.tiktok.com/@CHANNEL", {"channel": "CHANNEL"}),
        ("https://www.tiktok.com/@CHANNEL/live", {"channel": "CHANNEL"}),
    ]

    should_not_match = [
        "https://www.tiktok.com",
    ]
