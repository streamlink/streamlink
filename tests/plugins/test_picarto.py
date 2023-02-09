from streamlink.plugins.picarto import Picarto
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPicarto(PluginCanHandleUrl):
    __plugin__ = Picarto

    should_match = [
        "https://picarto.tv/example",
        "https://www.picarto.tv/example",
        "https://www.picarto.tv/example/videos/123456",
        "https://www.picarto.tv/streampopout/example/public",
        "https://www.picarto.tv/videopopout/123456",
    ]

    should_not_match = [
        "https://picarto.tv/",
        "https://www.picarto.tv/example/",
        "https://www.picarto.tv/example/videos/abc123",
        "https://www.picarto.tv/streampopout/example/notpublic",
        "https://www.picarto.tv/videopopout/abc123",
    ]
