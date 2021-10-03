from streamlink.plugins.orf_tvthek import ORFTVThek
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlORFTVThek(PluginCanHandleUrl):
    __plugin__ = ORFTVThek

    should_match = [
        "https://tvthek.orf.at/live/Christine-Lavant-Preis-2021/14139354",
        "https://tvthek.orf.at/profile/Aktuell-nach-eins/13887636/Aktuell-nach-eins/14107576",
    ]
