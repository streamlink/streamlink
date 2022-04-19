from streamlink.plugins.trovo import Trovo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTrovo(PluginCanHandleUrl):
    __plugin__ = Trovo

    should_match_groups = [
        ("https://trovo.live/UserName", {"user": "UserName"}),
        ("https://trovo.live/clip/clip_123", {"video_id": "clip_123"}),
        ("https://trovo.live/video/video_456", {"video_id": "video_456"}),
        ("https://www.trovo.live/UserName", {"user": "UserName"}),
        ("https://www.trovo.live/clip/clip_123", {"video_id": "clip_123"}),
        ("https://www.trovo.live/video/video_456", {"video_id": "video_456"}),
    ]

    should_not_match = [
        "https://trovo.live/",
        "https://www.trovo.live/",
    ]
