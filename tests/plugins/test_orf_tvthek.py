from streamlink.plugins.orf_tvthek import ORFTVThek
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlORFTVThek(PluginCanHandleUrl):
    __plugin__ = ORFTVThek

    should_match = [
        'http://tvthek.orf.at/live/Wetter/13953206',
    ]
