from streamlink.plugins.periscope import Periscope
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPeriscope(PluginCanHandleUrl):
    __plugin__ = Periscope

    should_match = [
        'https://www.periscope.tv/Pac12Networks/1BdGYRLyzMyJX',
        'https://www.periscope.tv/w/1YqKDdaoVXLKV',
        'https://www.pscp.tv/Pac12Networks/1gqGvpPlVLlxB'
    ]

    should_not_match = [
        'https://www.periscope.tv/',
        'https://www.pscp.tv/',
    ]
