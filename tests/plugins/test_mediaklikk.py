from streamlink.plugins.mediaklikk import Mediaklikk
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMediaklikk(PluginCanHandleUrl):
    __plugin__ = Mediaklikk

    should_match = [
        'https://www.mediaklikk.hu/duna-world-elo/',
        'https://www.mediaklikk.hu/duna-world-radio-elo',
        'https://www.mediaklikk.hu/m1-elo',
        'https://www.mediaklikk.hu/m2-elo',
        'https://mediaklikk.hu/video/hirado-2021-06-24-i-adas-6/',
        'https://m4sport.hu/elo/',
        'https://m4sport.hu/elo/?channelId=m4sport+',
    ]
