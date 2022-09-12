from streamlink.plugins.piczel import Piczel
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPiczel(PluginCanHandleUrl):
    __plugin__ = Piczel

    should_match_groups = [
        ("https://piczel.tv/watch/example", {"channel": "example"}),
    ]

    should_not_match = [
        "https://piczel.tv/",
        "https://piczel.tv/watch/",
    ]
