from streamlink.plugins.atpchallenger import AtpChallengerTour
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAtpChallenger(PluginCanHandleUrl):
    __plugin__ = AtpChallengerTour

    should_match = [
        "https://www.atptour.com/en/atp-challenger-tour/challenger-tv",
        "https://www.atptour.com/es/atp-challenger-tour/challenger-tv",
        "https://www.atptour.com/en/atp-challenger-tour/challenger-tv/challenger-tv-search-results/"
        + "2022-2785-ms005-zug-alexander-ritschard-vs-dominic-stricker/2022/2785/all",
    ]
