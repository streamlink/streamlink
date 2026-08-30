from streamlink.plugins.chzzk import Chzzk
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlChzzk(PluginCanHandleUrl):
    __plugin__ = Chzzk

    should_match_groups = [
        (("live", "https://chzzk.naver.com/live/CHANNEL_ID"), {"channel_id": "CHANNEL_ID"}),
        (("video", "https://chzzk.naver.com/video/VIDEO_ID"), {"video_id": "VIDEO_ID"}),
        (("clip", "https://chzzk.naver.com/clips/CLIP_ID"), {"clip_id": "CLIP_ID"}),
    ]
