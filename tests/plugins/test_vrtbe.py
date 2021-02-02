from streamlink.plugins.vrtbe import VRTbe
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVRTbe(PluginCanHandleUrl):
    __plugin__ = VRTbe

    should_match = [
        # LIVE
        "https://www.vrt.be/vrtnu/kanalen/canvas/",
        "https://www.vrt.be/vrtnu/kanalen/een/",
        "https://www.vrt.be/vrtnu/kanalen/ketnet/",
        # VOD
        "https://www.vrt.be/vrtnu/a-z/belfast-zoo/1/belfast-zoo-s1a14/",
        "https://www.vrt.be/vrtnu/a-z/sporza--korfbal/2017/sporza--korfbal-s2017-sporza-korfbal/",
        "https://www.vrt.be/vrtnu/a-z/de-grote-peter-van-de-veire-ochtendshow/2017/de-grote-peter-van-de-veire"
        + "-ochtendshow-s2017--en-parels-voor-de-zwijnen-ook/"
    ]
