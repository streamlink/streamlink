from streamlink.plugins.pluzz import Pluzz
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPluzz(PluginCanHandleUrl):
    __plugin__ = Pluzz

    should_match = [
        "https://www.france.tv/france-2/direct.html",
        "https://www.france.tv/france-3/direct.html",
        "https://www.france.tv/france-4/direct.html",
        "https://www.france.tv/france-5/direct.html",
        "https://www.france.tv/franceinfo/direct.html",
        "https://www.france.tv/france-2/journal-20h00/141003-edition-du-lundi-8-mai-2017.html",
        "https://france3-regions.francetvinfo.fr/bourgogne-franche-comte/tv/direct/franche-comte",
        "https://www.francetvinfo.fr/en-direct/tv.html",
        "https://www.francetvinfo.fr/meteo/orages/inondations-dans-le-gard-plus-de-deux-mois-de-pluie-en-quelques-heures-des"
        + "-degats-mais-pas-de-victime_4771265.html"
    ]
