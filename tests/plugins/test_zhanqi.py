from streamlink.plugins.zhanqi import Zhanqitv
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlZhanqitv(PluginCanHandleUrl):
    __plugin__ = Zhanqitv

    should_match = [
        "https://www.zhanqi.tv/lpl",
    ]
