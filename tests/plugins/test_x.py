from streamlink.plugins.x import X
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlX(PluginCanHandleUrl):
    __plugin__ = X

    should_match_groups = [
        (("live", "https://x.com/i/broadcasts/BROADCASTID"), {"id": "BROADCASTID"}),
        (("live", "https://www.x.com/i/broadcasts/BROADCASTID"), {"id": "BROADCASTID"}),
        (("live", "https://twitter.com/i/broadcasts/BROADCASTID"), {"id": "BROADCASTID"}),
        (("live", "https://www.twitter.com/i/broadcasts/BROADCASTID"), {"id": "BROADCASTID"}),
        (("vod", "https://x.com/USER/status/01234"), {"user": "USER", "id": "01234"}),
        (("vod", "https://x.com/USER/status/01234/video/56789"), {"user": "USER", "id": "01234", "idx": "56789"}),
    ]
