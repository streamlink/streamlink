from streamlink.plugins.btsports import BTSports
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBTSports(PluginCanHandleUrl):
    __plugin__ = BTSports

    should_match = [
        "https://sport.bt.com/btsportsplayer/football-match-1",
        "https://sport.bt.com/ss/Satellite/btsportsplayer/football-match-1",
    ]

    should_not_match = [
        "http://www.bt.com/",
        "http://bt.com/",
    ]
