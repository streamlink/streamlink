from streamlink.plugins.dogus import Dogus
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDogus(PluginCanHandleUrl):
    __plugin__ = Dogus

    should_match = [
        "http://eurostartv.com.tr/canli-izle",
        "https://www.kralmuzik.com.tr/tv/kral-pop-tv",
        "https://www.kralmuzik.com.tr/tv/kral-tv",
        "https://www.ntv.com.tr/canli-yayin/ntv?youtube=true",
        "https://www.startv.com.tr/canli-yayin",
    ]
