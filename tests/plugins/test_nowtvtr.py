from streamlink.plugins.nowtvtr import NowTVTR
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlFoxTR(PluginCanHandleUrl):
    __plugin__ = NowTVTR

    should_match = [
        "https://www.nowtv.com.tr/canli-yayin",
        "https://www.nowtv.com.tr/now-haber",
        "https://www.nowtv.com.tr/yayin-akisi",
        "https://www.nowtv.com.tr/Gaddar/bolumler",
        "https://www.nowtv.com.tr/Memet-Ozer-ile-Mutfakta/bolumler",
    ]
