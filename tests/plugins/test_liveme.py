from streamlink.plugins.liveme import LiveMe
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLiveMe(PluginCanHandleUrl):
    __plugin__ = LiveMe

    should_match = [
        "http://www.liveme.com/live.html?videoid=12312312312312312312",
        "http://www.liveme.com/live.html?videoid=23123123123123123123&countryCode=undefined"
    ]

    should_not_match = [
        "http://www.liveme.com/",
        "http://www.liveme.com/explore.html",
        "http://www.liveme.com/media/play"
    ]
