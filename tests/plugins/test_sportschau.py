from streamlink.plugins.sportschau import Sportschau
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSportschau(PluginCanHandleUrl):
    __plugin__ = Sportschau

    should_match = [
        "https://www.sportschau.de/fussball/uefa-euro-2024/spaniens-europameister-begeistert-empfangen,em-spanien-feier-100.html",
        "https://www.sportschau.de/olympia/live/schwimmen-finals-m-f,livestream-olympia-schwimmen-110.html",
        "https://www.sportschau.de/podcasts/sportschau-olympia-podcast/tag-6-vier-gewinnt,audio-tag-6-vier-gewinnt-100.html",
    ]
