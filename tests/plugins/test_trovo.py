from streamlink.plugins.trovo import Trovo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTrovo(PluginCanHandleUrl):
    __plugin__ = Trovo

    should_match_groups = [
        ("https://trovo.live/s/UserName", {"user": "UserName"}),
        ("https://trovo.live/s/UserName/abc", {"user": "UserName"}),
        ("https://trovo.live/s/UserName/123", {"user": "UserName"}),
        ("https://trovo.live/s/UserName/123?vid=vc-456&adtag=", {"user": "UserName", "video_id": "vc-456"}),
        ("https://trovo.live/s/UserName/123?vid=ltv-1_2_3&adtag=", {"user": "UserName", "video_id": "ltv-1_2_3"}),
        ("https://www.trovo.live/s/UserName", {"user": "UserName"}),
        ("https://www.trovo.live/s/UserName/abc", {"user": "UserName"}),
        ("https://www.trovo.live/s/UserName/123", {"user": "UserName"}),
        ("https://www.trovo.live/s/UserName/123?vid=vc-456&adtag=", {"user": "UserName", "video_id": "vc-456"}),
        ("https://www.trovo.live/s/UserName/123?vid=ltv-1_2_3&adtag=", {"user": "UserName", "video_id": "ltv-1_2_3"}),
    ]

    should_not_match = [
        "https://trovo.live/",
        "https://www.trovo.live/",
        "https://www.trovo.live/s/",
        "https://www.trovo.live/other/",
    ]
