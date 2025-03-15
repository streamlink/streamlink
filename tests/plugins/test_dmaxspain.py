from streamlink.plugins.dmaxspain import DmaxSpain
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDmax(PluginCanHandleUrl):
    __plugin__ = DmaxSpain

    should_match = [
        "https://dmax.marca.com/en-directo",
    ]

    should_not_match = [
        "https://dmax.marca.com/series",
        "https://dmax.marca.com",
        "https://marca.com",
    ]
