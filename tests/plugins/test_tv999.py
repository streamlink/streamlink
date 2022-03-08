from streamlink.plugins.tv999 import TV999
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV999(PluginCanHandleUrl):
    __plugin__ = TV999

    should_match = [
        "http://tv999.bg/live.html",
        "http://www.tv999.bg/live.html",
        "https://tv999.bg/live",
        "https://tv999.bg/live.html",
        "https://www.tv999.bg/live.html",
    ]

    should_not_match = [
        "http://tv999.bg/",
    ]
