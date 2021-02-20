from streamlink.plugins.live_russia_tv import LiveRussia
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLiveRussiaTv(PluginCanHandleUrl):
    __plugin__ = LiveRussia

    should_match = [
        "https://live.russia.tv/channel/1",
        "https://live.russia.tv/channel/199",
        "https://live.russia.tv/",
        "https://live.russia.tv/video/show/brand_id/60473/episode_id/2187772/video_id/2204594"
    ]
