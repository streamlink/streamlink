from streamlink.plugins.twitcasting import TwitCasting
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTwitCasting(PluginCanHandleUrl):
    __plugin__ = TwitCasting

    should_match = [
        'https://twitcasting.tv/c:kk1992kkkk',
        'https://twitcasting.tv/icchy8591/movie/566593738',
    ]
