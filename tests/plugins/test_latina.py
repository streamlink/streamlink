from streamlink.plugins.latina import Latina
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLatina(PluginCanHandleUrl):
    __plugin__ = Latina

    should_match = [
        'http://www.latina.pe/tvenvivo/',
    ]

    should_not_match = [
        'http://www.latina.pe/',
    ]
