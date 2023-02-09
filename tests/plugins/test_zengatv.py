from streamlink.plugins.zengatv import ZengaTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlZengaTV(PluginCanHandleUrl):
    __plugin__ = ZengaTV

    should_match = [
        "http://www.zengatv.com/indiatoday.html",
        "http://www.zengatv.com/live/87021a6d-411e-11e2-b4c6-7071bccc85ac.html",
        "http://zengatv.com/indiatoday.html",
        "http://zengatv.com/live/87021a6d-411e-11e2-b4c6-7071bccc85ac.html",
    ]

    should_not_match = [
        "http://www.zengatv.com",
        "http://www.zengatv.com/",
    ]
