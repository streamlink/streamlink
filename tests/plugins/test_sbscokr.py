from streamlink.plugins.sbscokr import SBScokr
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSBScokr(PluginCanHandleUrl):
    __plugin__ = SBScokr

    should_match = [
        'https://play.sbs.co.kr/onair/pc/index.html',
        'http://play.sbs.co.kr/onair/pc/index.html',
    ]
