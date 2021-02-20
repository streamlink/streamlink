from streamlink.plugins.tvtoya import TVToya
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVRPlus(PluginCanHandleUrl):
    __plugin__ = TVToya

    should_match = [
        "https://tvtoya.pl/live",
        "http://tvtoya.pl/live",
    ]

    should_not_match = [
        "https://tvtoya.pl",
        "http://tvtoya.pl",
        "http://tvtoya.pl/other-page",
        "http://tvtoya.pl/",
        "https://tvtoya.pl/",
    ]
