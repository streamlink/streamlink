from streamlink.plugins.pandalive import Pandalive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPandalive(PluginCanHandleUrl):
    __plugin__ = Pandalive

    should_match_groups = [
        ("https://www.pandalive.co.kr/live/play/CHANNEL", {"channel": "CHANNEL"}),
        ("https://w2.pandalive.co.kr/en/play/CHANNEL", {"channel": "CHANNEL"}),
    ]
