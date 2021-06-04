from streamlink.plugins.mediaklikk import Mediaklikk
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMediaklikk(PluginCanHandleUrl):
    __plugin__ = Mediaklikk

    should_match = [
        'https://www.mediaklikk.hu/duna-world-elo/',
        'https://www.mediaklikk.hu/duna-world-radio-elo',
        'https://www.mediaklikk.hu/m1-elo',
        'https://www.mediaklikk.hu/m2-elo',
        'https://m4sport.hu/elo/',
        'https://m4sport.hu/elo/?channelId=m4sport+',
        'https://m4sport.hu/elo/?showchannel=mtv4plus',
    ]

    should_not_match = [
        'https://www.mediaklikk.hu',
        'https://m4sport.hu',
    ]
