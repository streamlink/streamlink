from streamlink.plugins.sbscokr import SBScokr
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSBScokr(PluginCanHandleUrl):
    __plugin__ = SBScokr

    should_match_groups = [
        # regular channels
        ("https://www.sbs.co.kr/live/S01", {"channel": "S01"}),
        ("https://www.sbs.co.kr/live/S01?div=live_list", {"channel": "S01"}),
        # "virtual" channels
        ("https://www.sbs.co.kr/live/S21", {"channel": "S21"}),
        ("https://www.sbs.co.kr/live/S21?div=live_list", {"channel": "S21"}),
    ]
