from streamlink.plugins.pandalive import Pandalive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPandalive(PluginCanHandleUrl):
    __plugin__ = Pandalive

    should_match = [
        "http://pandalive.co.kr/",
        "http://pandalive.co.kr/any/path",
        "http://www.pandalive.co.kr/",
        "http://www.pandalive.co.kr/any/path",
        "https://pandalive.co.kr/",
        "https://pandalive.co.kr/any/path",
        "https://www.pandalive.co.kr/",
        "https://www.pandalive.co.kr/any/path",
    ]
