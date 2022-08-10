from streamlink.plugins.deutschewelle import DeutscheWelle
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDeutscheWelle(PluginCanHandleUrl):
    __plugin__ = DeutscheWelle

    should_match = [
        # Live: en/EN (no channel selection)
        "https://www.dw.com/en/live-tv/s-100825",

        # Live: de/DE (default channel)
        "https://www.dw.com/de/live-tv/s-100817",
        # Live: de/DE (selected channel)
        "https://www.dw.com/de/live-tv/s-100817?channel=5",
        # Live: de/EN (selected channel)
        "https://www.dw.com/de/live-tv/s-100817?channel=1",

        # Live: es/ES (default channel)
        "https://www.dw.com/es/tv-en-vivo/s-100837",
        # Live: es/ES (selected channel)
        "https://www.dw.com/es/tv-en-vivo/s-100837?channel=3",
        # Live: es/DE (selected channel)
        "https://www.dw.com/es/tv-en-vivo/s-100837?channel=5",

        # VOD
        "https://www.dw.com/en/top-stories-in-90-seconds/av-49496622",

        # Audio
        "https://www.dw.com/en/womens-euros-2022-the-end/av-62738085",
    ]
