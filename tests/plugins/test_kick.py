from streamlink.plugins.kick import Kick
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlKick(PluginCanHandleUrl):
    __plugin__ = Kick

    should_match_groups = [
        (
            ("live", "https://kick.com/LIVE_CHANNEL"),
            {"channel": "LIVE_CHANNEL"},
        ),
        (
            ("vod", "https://kick.com/video/VIDEO_ID"),
            {"vod": "VIDEO_ID"},
        ),
        (
            ("vod", "https://kick.com/VIDEO_CHANNEL/videos/VIDEO_ID"),
            {"vod": "VIDEO_ID"},
        ),
        (
            ("clip", "https://kick.com/CLIP_CHANNEL?clip=CLIP_ID&foo=bar"),
            {"channel": "CLIP_CHANNEL", "clip": "CLIP_ID"},
        ),
        (
            ("clip", "https://kick.com/CLIP_CHANNEL/clips/CLIP_ID?foo=bar"),
            {"channel": "CLIP_CHANNEL", "clip": "CLIP_ID"},
        ),
        (
            ("clip", "https://kick.com/CLIP_CHANNEL/clips/CLIP_ID?clip=CLIP_ID_FROM_QUERY_STRING&foo=bar"),
            {"channel": "CLIP_CHANNEL", "clip": "CLIP_ID"},
        ),
    ]
