from streamlink.plugins.tv5monde import TV5Monde
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV5Monde(PluginCanHandleUrl):
    __plugin__ = TV5Monde

    should_match = [
        "http://live.tv5monde.com/fbs.html",
        "https://www.tv5monde.com/emissions/episode/version-francaise-vf-83",
        "https://revoir.tv5monde.com/toutes-les-videos/cinema/je-ne-reve-que-de-vous",
        "https://revoir.tv5monde.com/toutes-les-videos/documentaires/des-russes-blancs-des-russes-blancs",
        "https://information.tv5monde.com/video/la-diplomatie-francaise-est-elle-en-crise",
        "https://afrique.tv5monde.com/videos/exclusivites-web/les-tutos-de-magloire/season-1/episode-1",
        "https://www.tivi5mondeplus.com/conte-nous/episode-25",
    ]
