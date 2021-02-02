from streamlink.plugins.piczel import Piczel
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPiczel(PluginCanHandleUrl):
    __plugin__ = Piczel

    should_match = [
        'https://piczel.tv/watch/example',
    ]
