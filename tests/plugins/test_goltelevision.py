from streamlink.plugins.goltelevision import GOLTelevision
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlEuronews(PluginCanHandleUrl):
    __plugin__ = GOLTelevision

    should_match = [
        "http://www.goltelevision.com/live",
        "http://goltelevision.com/live",
        "https://goltelevision.com/live",
        "https://www.goltelevision.com/live",
    ]
