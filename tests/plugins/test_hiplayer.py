from streamlink.plugins.hiplayer import HiPlayer
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHiPlayer(PluginCanHandleUrl):
    __plugin__ = HiPlayer

    should_match = [
        "https://www.alwasat.ly/any",
        "https://www.alwasat.ly/any/path",
        "https://www.cnbcarabia.com/any",
        "https://www.cnbcarabia.com/any/path",
        "https://www.media.gov.kw/any",
        "https://www.media.gov.kw/any/path",
        "https://rotana.net/any",
        "https://rotana.net/any/path",
    ]
