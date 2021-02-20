from streamlink.plugins.rotana import Rotana
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRotana(PluginCanHandleUrl):
    __plugin__ = Rotana

    should_match = [
        'https://rotana.net/live-classic',
        'https://rotana.net/live-music',
    ]
