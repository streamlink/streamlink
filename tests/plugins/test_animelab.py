from streamlink.plugins.animelab import AnimeLab
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAnimeLab(PluginCanHandleUrl):
    __plugin__ = AnimeLab

    should_match = [
        'https://www.animelab.com/player/123',
        'https://animelab.com/player/123',
    ]
