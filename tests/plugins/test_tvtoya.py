from streamlink.plugins.tvtoya import TVToya
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVRPlus(PluginCanHandleUrl):
    __plugin__ = TVToya

    should_match = [
        "http://tvtoya.pl/player/live",
        "https://tvtoya.pl/player/live",
    ]

    should_not_match = [
        "http://tvtoya.pl",
        "http://tvtoya.pl/",
        "http://tvtoya.pl/live",
        "https://tvtoya.pl",
        "https://tvtoya.pl/",
        "https://tvtoya.pl/live",
    ]
