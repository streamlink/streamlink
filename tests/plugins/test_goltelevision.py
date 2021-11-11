from streamlink.plugins.goltelevision import GOLTelevision
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlEuronews(PluginCanHandleUrl):
    __plugin__ = GOLTelevision

    should_match = [
        "http://goltelevision.com/en-directo",
        "http://www.goltelevision.com/en-directo",
        "https://goltelevision.com/en-directo",
        "https://www.goltelevision.com/en-directo",
    ]

    should_not_match = [
        "http://goltelevision.com/live",
        "http://www.goltelevision.com/live",
        "https://goltelevision.com/live",
        "https://www.goltelevision.com/live",
    ]
