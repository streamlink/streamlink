from streamlink.plugins.cnews import CNEWS
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCNEWS(PluginCanHandleUrl):
    __plugin__ = CNEWS

    should_match = [
        "http://www.cnews.fr/le-direct",
        "http://www.cnews.fr/direct",
        "http://www.cnews.fr/emission/2018-06-12/meteo-du-12062018-784730",
        "http://www.cnews.fr/emission/2018-06-12/le-journal-des-faits-divers-du-12062018-784704"
    ]
