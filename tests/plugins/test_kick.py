from streamlink.plugins.kick import Kick
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlKick(PluginCanHandleUrl):
    __plugin__ = Kick

    should_match_groups = [
        (("live", "https://kick.com/LIVE_CHANNEL"), {"channel": "LIVE_CHANNEL"}),
        (("vod", "https://kick.com/video/VIDEO_ID"), {"vod": "VIDEO_ID"}),
        (("clip", "https://kick.com/CLIP_CHANNEL?clip=CLIP_ID"), {"channel": "CLIP_CHANNEL", "clip": "CLIP_ID"}),
    ]
