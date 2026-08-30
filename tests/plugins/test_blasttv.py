from streamlink.plugins.blasttv import BlastTv
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBlastTv(PluginCanHandleUrl):
    __plugin__ = BlastTv

    should_match_groups = [
        # live
        (("live", "https://blast.tv"), {}),
        (("live", "https://blast.tv/"), {}),
        (("live", "https://blast.tv/live"), {}),
        (("live", "https://blast.tv/live/"), {}),
        (("live", "https://blast.tv/live/a"), {"channel": "a"}),
        (("live", "https://blast.tv/live/co-stream"), {"channel": "co-stream"}),
        (("live", "https://blast.tv/live/americas1"), {"channel": "americas1"}),
        # external streams (at the time of testing)
        (("live", "https://blast.tv/live/f"), {"channel": "f"}),
        # VODs
        (
            ("vod", "https://blast.tv/cs/tournaments/rivals-2025-season-1/match/bfaaa42e/falcons-vitality"),
            {"game": "cs", "shortid": "bfaaa42e"},
        ),
        (
            ("vod", "https://blast.tv/cs/tournaments/open-2025-season-1/match/24ff9d6c/vitality-mouz"),
            {"game": "cs", "shortid": "24ff9d6c"},
        ),
        # external VODs
        (
            ("vod", "https://blast.tv/dota/tournaments/blast-slam-iii/match/acabb915/falcons-tundra"),
            {"game": "dota", "shortid": "acabb915"},
        ),
    ]

    should_not_match = [
        "https://blast.tv/a",
    ]
