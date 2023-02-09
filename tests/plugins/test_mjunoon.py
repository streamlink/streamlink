from streamlink.plugins.mjunoon import Mjunoon
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMjunoon(PluginCanHandleUrl):
    __plugin__ = Mjunoon

    should_match = [
        "https://mjunoon.tv/news-live",
        "http://mjunoon.tv/watch/some-long-vod-name23456",
        "https://www.mjunoon.tv/other-live",
        "https://www.mjunoon.tv/watch/something-else-2321",
    ]

    should_not_match = [
        "https://mjunoon.com",
    ]
