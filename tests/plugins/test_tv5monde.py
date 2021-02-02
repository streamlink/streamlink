from streamlink.plugins.tv5monde import TV5Monde
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV5Monde(PluginCanHandleUrl):
    __plugin__ = TV5Monde

    should_match = [
        "http://live.tv5monde.com/fbs.html",
        "http://information.tv5monde.com/les-jt/monde",
        "http://information.tv5monde.com/info/legislatives-en-france-carnet-de-campagne-a-montreal-172631",
        "http://www.tv5mondeplusafrique.com/video_karim_ben_khelifa_je_ne_suis_pas_votre_negre_oumou_sangare"
        + "_4658602.html",
        "http://www.tv5mondeplus.com/toutes-les-videos/information/tv5monde-le-journal-edition-du-02-06-17-11h00",
        "http://focus.tv5monde.com/prevert/le-roi-et-loiseau/"
    ]

    should_not_match = [
        "http://www.tv5.ca/",
    ]
