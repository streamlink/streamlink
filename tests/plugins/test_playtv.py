from streamlink.plugins.playtv import PlayTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPlayTV(PluginCanHandleUrl):
    __plugin__ = PlayTV

    should_match = [
        "http://playtv.fr/television/arte",
        "http://playtv.fr/television/arte/",
        "http://playtv.fr/television/tv5-monde",
        "http://playtv.fr/television/france-24-english/",
        "http://play.tv/live-tv/9/arte",
        "http://play.tv/live-tv/9/arte/",
        "http://play.tv/live-tv/21/tv5-monde",
        "http://play.tv/live-tv/50/france-24-english/",
    ]

    should_not_match = [
        "http://playtv.fr/television/",
        "http://playtv.fr/replay-tv/",
        "http://play.tv/live-tv/",
    ]
