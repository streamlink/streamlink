from streamlink.plugins.teamliquid import Teamliquid
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTeamliquid(PluginCanHandleUrl):
    __plugin__ = Teamliquid

    should_match = [
        "http://www.teamliquid.net/video/streams/Classic%20BW%20VODs",
        "http://teamliquid.net/video/streams/iwl-fuNny",
        "http://www.teamliquid.net/video/streams/OGamingTV%20SC2",
        "http://www.teamliquid.net/video/streams/Check",
        "https://tl.net/video/streams/GSL",
    ]

    should_not_match = [
        "http://www.teamliquid.net/Classic%20BW%20VODs",
        "http://www.teamliquid.net/video/Check",
        "http://www.teamliquid.com/video/streams/Check",
        "http://www.teamliquid.net/video/stream/Check",
    ]
