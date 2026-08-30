from streamlink.plugins.rtvs import Rtvs
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRtvs(PluginCanHandleUrl):
    __plugin__ = Rtvs

    should_match = [
        "https://www.rtvs.sk/televizia/live-1",
        "https://www.rtvs.sk/televizia/live-2",
        "https://www.rtvs.sk/televizia/live-3",
        "https://www.rtvs.sk/televizia/live-o",
        "https://www.rtvs.sk/televizia/live-rtvs",
        "https://www.rtvs.sk/televizia/live-nr-sr",
        "https://www.rtvs.sk/televizia/sport",
    ]

    should_not_match = [
        "http://www.rtvs.sk/",
        "http://www.rtvs.sk/televizia/archiv",
        "http://www.rtvs.sk/televizia/program",
    ]
