from streamlink.plugins.theplatform import ThePlatform
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlThePlatform(PluginCanHandleUrl):
    __plugin__ = ThePlatform

    should_match = [
        'https://player.theplatform.com/p/',
        'http://player.theplatform.com/p/',
    ]
