from streamlink.plugins.ntv import NTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNTV(PluginCanHandleUrl):
    __plugin__ = NTV

    should_match = [
        'https://www.ntv.ru/air/',
        'http://www.ntv.ru/air/'
    ]

    should_not_match = [
        'https://www.ntv.ru/',
        'http://www.ntv.ru/'
    ]
