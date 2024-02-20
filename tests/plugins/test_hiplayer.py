from streamlink.plugins.hiplayer import HiPlayer
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHiPlayer(PluginCanHandleUrl):
    __plugin__ = HiPlayer

    should_match = [
        ("alwasatly", "https://alwasat.ly/live"),
    ]
