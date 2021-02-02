from streamlink.plugins.picarto import Picarto
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPicarto(PluginCanHandleUrl):
    __plugin__ = Picarto

    should_match = [
        'https://picarto.tv/example',
        'https://picarto.tv/videopopout/example_2020.00.00.00.00.00_nsfw.mkv',
    ]
