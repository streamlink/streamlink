from streamlink.plugins.pandalive import Pandalive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPandalive(PluginCanHandleUrl):
    __plugin__ = Pandalive

    should_match = [
        "https://www.pandalive.co.kr/live/play/pocet00",
        "https://www.pandalive.co.kr/live/play/rladbfl1208",
    ]
