from streamlink.plugins.tv5monde import TV5Monde
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV5Monde(PluginCanHandleUrl):
    __plugin__ = TV5Monde

    should_match = [
        "https://live.tv5monde.com/fbs.html",
        "https://europe.tv5monde.com/fr/direct",
        "https://maghreb-orient.tv5monde.com/fr/direct",
        "https://revoir.tv5monde.com/toutes-les-videos/documentaires/sauver-notre-dame-sauver-notre-dame-14-04-2020",
        "https://information.tv5monde.com/video/la-diplomatie-francaise-est-elle-en-crise",
        "https://afrique.tv5monde.com/videos/afrykas-et-la-boite-magique",
        "https://www.tivi5mondeplus.com/conte-nous/episode-25",
    ]
