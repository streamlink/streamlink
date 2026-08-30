from streamlink.plugins.btv import BTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBTV(PluginCanHandleUrl):
    __plugin__ = BTV

    should_match = [
        "https://btvplus.bg/live",
        "https://btvplus.bg/live/",
        "https://www.btvplus.bg/live/",
    ]
