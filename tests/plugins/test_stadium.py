from streamlink.plugins.stadium import Stadium
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlStadium(PluginCanHandleUrl):
    __plugin__ = Stadium

    should_match = [
        "http://www.watchstadium.com/live",
        "https://www.watchstadium.com/live",
        "https://watchstadium.com/live",
        "http://watchstadium.com/live",
        "https://watchstadium.com/sport/college-football/",
    ]
