from streamlink.plugins.pluzz import Pluzz
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPluzz(PluginCanHandleUrl):
    __plugin__ = Pluzz

    should_match = [
        ("francetv", "https://www.france.tv/france-2/direct.html"),
        ("francetv", "https://www.france.tv/france-3/direct.html"),
        ("francetv", "https://www.france.tv/france-4/direct.html"),
        ("francetv", "https://www.france.tv/france-5/direct.html"),
        ("francetv", "https://www.france.tv/franceinfo/direct.html"),
        ("francetv", "https://www.france.tv/france-2/journal-20h00/141003-edition-du-lundi-8-mai-2017.html"),
        (
            "francetvinfofr",
            "https://www.francetvinfo.fr/en-direct/tv.html",
        ),
        (
            "francetvinfofr",
            "https://www.francetvinfo.fr/meteo/orages/inondations-dans-le-gard-plus-de-deux-mois-de-pluie-en-quelques-heures-des-degats-mais-pas-de-victime_4771265.html",
        ),
        (
            "francetvinfofr",
            "https://france3-regions.francetvinfo.fr/bourgogne-franche-comte/direct/franche-comte",
        ),
        (
            "francetvinfofr",
            "https://la1ere.francetvinfo.fr/programme-video/france-3_outremer-ledoc/diffusion/2958951-polynesie-les-sages-de-l-ocean.html",
        ),
        (
            "francetvinfofr",
            "https://la1ere.francetvinfo.fr/info-en-continu-24-24",
        ),
    ]
