from streamlink.plugins.huya import Huya
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHuya(PluginCanHandleUrl):
    __plugin__ = Huya

    should_match = [
        "http://www.huya.com/123123123",
        "http://www.huya.com/name",
        "https://www.huya.com/123123123",
        "https://www.huya.com/name",
    ]

    should_not_match = [
        "http://www.huya.com",
        "https://www.huya.com",
    ]
