from streamlink.plugins.tiktok import TikTok
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTikTok(PluginCanHandleUrl):
    __plugin__ = TikTok

    should_match_groups = [
        (("live", "https://www.tiktok.com/@LIVE"), {"channel": "LIVE"}),
        (("live", "https://www.tiktok.com/@LIVE/live"), {"channel": "LIVE"}),
        (("video", "https://www.tiktok.com/@VIDEO/video/0123456789"), {"channel": "VIDEO", "id": "0123456789"}),
    ]

    should_not_match = [
        "https://www.tiktok.com",
    ]
