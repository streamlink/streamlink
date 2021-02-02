from streamlink.plugins.rtbf import RTBF
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRTBF(PluginCanHandleUrl):
    __plugin__ = RTBF

    should_match = [
        "https://www.rtbf.be/auvio/direct_doc-shot?lid=122046#/",
        "https://www.rtbf.be/auvio/emissions/detail_dans-la-toile?id=11493",
        "http://www.rtbfradioplayer.be/radio/liveradio/purefm",
    ]

    should_not_match = [
        "http://www.rtbf.be/",
        "http://www.rtbf.be/auvio",
        "http://www.rtbfradioplayer.be/",
    ]
