from streamlink.plugins.openrectv import OPENRECtv
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOPENRECtv(PluginCanHandleUrl):
    __plugin__ = OPENRECtv

    should_match = [
        "https://www.openrec.tv/live/DXRLAPSGTpx",
        "https://www.openrec.tv/movie/JsDw3rAV2Rj",
    ]

    should_not_match = [
        "https://www.openrec.tv/",
    ]
