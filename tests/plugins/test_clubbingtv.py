from streamlink.plugins.clubbingtv import ClubbingTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlClubbingTV(PluginCanHandleUrl):
    __plugin__ = ClubbingTV

    should_match = [
        "https://www.clubbingtv.com/live",
        "https://www.clubbingtv.com/video/play/3950/moonlight/",
        "https://www.clubbingtv.com/video/play/2897",
        "https://www.clubbingtv.com/tomer-s-pick/",
    ]
