from streamlink.plugins.rtve import Rtve
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRtve(PluginCanHandleUrl):
    __plugin__ = Rtve

    should_match = [
        'https://www.rtve.es/play/videos/directo/la-1/',
        'https://www.rtve.es/play/videos/directo/canales-lineales/24h/',
        'https://www.rtve.es/play/videos/rebelion-en-el-reino-salvaje/mata-reyes/5803959/',
    ]

    should_not_match = [
        'https://www.rtve.es',
        'http://www.rtve.es/directo/la-1',
        'http://www.rtve.es/directo/la-2/',
        'http://www.rtve.es/directo/teledeporte/',
        'http://www.rtve.es/directo/canal-24h/',
        'http://www.rtve.es/infantil/directo/',
    ]
