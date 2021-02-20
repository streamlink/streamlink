from streamlink.plugins.btv import BTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBTV(PluginCanHandleUrl):
    __plugin__ = BTV

    should_match = [
        "http://btvplus.bg/live",
        "http://btvplus.bg/live/",
        "http://www.btvplus.bg/live/",
    ]
