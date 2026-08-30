from streamlink.plugins.dlive import DLive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDLive(PluginCanHandleUrl):
    __plugin__ = DLive

    should_match_groups = [
        (("live", "https://dlive.tv/cryptokaprika"), {"channel": "cryptokaprika"}),
        (("live", "https://dlive.tv/cryptokaprika?query"), {"channel": "cryptokaprika"}),
        (("live", "https://dlive.tv/cryptokaprika#hash"), {"channel": "cryptokaprika"}),
        (("vod", "https://dlive.tv/p/countrycafebgky+oLCFcknSR"), {"video": "countrycafebgky+oLCFcknSR"}),
        (("vod", "https://dlive.tv/p/countrycafebgky+oLCFcknSR?query"), {"video": "countrycafebgky+oLCFcknSR"}),
        (("vod", "https://dlive.tv/p/countrycafebgky+oLCFcknSR#hash"), {"video": "countrycafebgky+oLCFcknSR"}),
    ]

    should_not_match = [
        "https://dlive.tv/",
    ]
