from streamlink.plugins.pluzz import Pluzz
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPluzz(PluginCanHandleUrl):
    __plugin__ = Pluzz

    should_match = [
        "https://www.france.tv/france-2/direct.html",
        "https://www.france.tv/france-3/direct.html",
        "https://www.france.tv/france-3-franche-comte/direct.html",
        "https://www.france.tv/france-4/direct.html",
        "https://www.france.tv/france-5/direct.html",
        "https://www.france.tv/france-o/direct.html",
        "https://www.france.tv/franceinfo/direct.html",
        "https://www.france.tv/france-2/journal-20h00/141003-edition-du-lundi-8-mai-2017.html",
        "https://www.france.tv/france-o/underground/saison-1/132187-underground.html",
        "http://www.ludo.fr/heros/the-batman",
        "http://www.ludo.fr/heros/il-etait-une-fois-la-vie",
        "http://www.zouzous.fr/heros/oui-oui",
        "http://www.zouzous.fr/heros/marsupilami-1",
        "http://france3-regions.francetvinfo.fr/bourgogne-franche-comte/tv/direct/franche-comte",
        "http://sport.francetvinfo.fr/roland-garros/direct",
        "http://sport.francetvinfo.fr/roland-garros/live-court-3",
        "http://sport.francetvinfo.fr/roland-garros/andy-murray-gbr-1-andrey-kuznetsov-rus-1er-tour-court"
        + "-philippe-chatrier",
        "https://www.francetvinfo.fr/en-direct/tv.html"
    ]

    should_not_match = [
        "http://www.france.tv/",
        "http://pluzz.francetv.fr/",
        "http://www.ludo.fr/",
        "http://www.ludo.fr/jeux",
        "http://www.zouzous.fr/",
    ]
