from streamlink.plugins.picarto import Picarto
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPicarto(PluginCanHandleUrl):
    __plugin__ = Picarto

    should_match = [
        'https://picarto.tv/example',
        'https://www.picarto.tv/example',
        'https://www.picarto.tv/streampopout/example/public',
        'https://www.picarto.tv/videopopout/123456',
        'https://www.picarto.tv/example?tab=videos&id=123456',
    ]
