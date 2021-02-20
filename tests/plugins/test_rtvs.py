from streamlink.plugins.rtvs import Rtvs
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRtvs(PluginCanHandleUrl):
    __plugin__ = Rtvs

    should_match = [
        'http://www.rtvs.sk/televizia/live-1',
        'http://www.rtvs.sk/televizia/live-2',
        'http://www.rtvs.sk/televizia/live-o',
    ]

    should_not_match = [
        'http://www.rtvs.sk/',
    ]
