from streamlink.plugins.nimotv import NimoTV
from tests.plugins import PluginCanHandleUrl


class TestPluginNimoTV(PluginCanHandleUrl):
    __plugin__ = NimoTV

    should_match = [
        'http://www.nimo.tv/live/737614',
        'https://www.nimo.tv/live/737614',
        'http://www.nimo.tv/sanz',
        'https://www.nimo.tv/sanz',
        'https://m.nimo.tv/user',
    ]
