from streamlink.plugins.rtve import Rtve
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRtve(PluginCanHandleUrl):
    __plugin__ = Rtve

    should_match = [
        'http://www.rtve.es/directo/la-1',
        'http://www.rtve.es/directo/la-2/',
        'http://www.rtve.es/directo/teledeporte/',
        'http://www.rtve.es/directo/canal-24h/',
        'http://www.rtve.es/infantil/directo/',
    ]

    should_not_match = [
        'https://www.rtve.es',
    ]
