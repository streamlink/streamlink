from streamlink.plugins.huya import Huya
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHuya(PluginCanHandleUrl):
    __plugin__ = Huya

    should_match_groups = [
        ("https://www.huya.com/CHANNEL", {"channel": "CHANNEL"}),
    ]

    should_not_match = [
        "https://www.huya.com",
    ]
