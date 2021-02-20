from streamlink.plugins.idf1 import IDF1
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlIDF1(PluginCanHandleUrl):
    __plugin__ = IDF1

    should_match = [
        "https://www.idf1.fr/live",
        "https://www.idf1.fr/videos/jlpp/best-of-2018-02-24-partie-2.html",
        "http://www.idf1.fr/videos/buzz-de-noel/partie-2.html",
    ]

    should_not_match = [
        "https://www.idf1.fr/",
        "https://www.idf1.fr/videos",
        "https://www.idf1.fr/programmes/emissions/idf1-chez-vous.html",
    ]
