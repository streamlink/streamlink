from streamlink.plugins.huajiao import Huajiao
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHuajiao(PluginCanHandleUrl):
    __plugin__ = Huajiao

    should_match = [
        "http://www.huajiao.com/l/123123123",
        "https://www.huajiao.com/l/123123123",
    ]
