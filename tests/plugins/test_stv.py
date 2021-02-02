from streamlink.plugins.stv import STV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSTV(PluginCanHandleUrl):
    __plugin__ = STV

    should_match = [
        'https://player.stv.tv/live',
        'http://player.stv.tv/live',
    ]
