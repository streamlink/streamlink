from streamlink.plugins.drdk import DRDK
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDRDK(PluginCanHandleUrl):
    __plugin__ = DRDK

    should_match = [
        'https://www.dr.dk/drtv/kanal/dr1_20875',
        'https://www.dr.dk/drtv/kanal/dr2_20876',
        'https://www.dr.dk/drtv/kanal/dr-ramasjang_20892',
    ]

    should_not_match = [
        'https://www.dr.dk/tv/live/dr1',
        'https://www.dr.dk/tv/live/dr2',
        'https://www.dr.dk/tv/se/matador/matador-saeson-3/matador-15-24',
    ]
