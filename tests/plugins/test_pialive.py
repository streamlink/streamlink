from streamlink.plugins.pialive import PiaLive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPiaLive(PluginCanHandleUrl):
    __plugin__ = PiaLive

    should_match_groups = [
        (
            "https://player.pia-live.jp/stream/4JagFBEIM14s_hK9aXHKf3k3F3bY5eoHFQxu68TC6krUDqGOwN4d61dCWQYOd6CTxl4hjya9dsfEZGsM4uGOUdax60lEI4twsXGXf7crmz8Gk__GhupTrWxA7RFRVt76",
            {"video_key": "4JagFBEIM14s_hK9aXHKf3k3F3bY5eoHFQxu68TC6krUDqGOwN4d61dCWQYOd6CTxl4hjya9dsfEZGsM4uGOUdax60lEI4twsXGXf7crmz8Gk__GhupTrWxA7RFRVt76"},
        ),
    ]

    should_not_match = [
        "https://player.pia-live.jp/",
    ]
