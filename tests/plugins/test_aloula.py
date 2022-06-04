from streamlink.plugins.aloula import Aloula
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAloula(PluginCanHandleUrl):
    __plugin__ = Aloula

    should_match_groups = [
        ("https://www.aloula.sa/live/slug", {"live_slug": "slug"}),
        ("https://www.aloula.sa/en/live/slug", {"live_slug": "slug"}),
        ("https://www.aloula.sa/de/live/slug/abc", {"live_slug": "slug"}),
        ("https://www.aloula.sa/episode/123", {"vod_id": "123"}),
        ("https://www.aloula.sa/en/episode/123", {"vod_id": "123"}),
        ("https://www.aloula.sa/episode/123abc/456", {"vod_id": "123"}),
        ("https://www.aloula.sa/de/episode/123abc/456", {"vod_id": "123"}),
        ("https://www.aloula.sa/episode/123?continue=8", {"vod_id": "123"}),
        ("https://www.aloula.sa/xx/episode/123?continue=8", {"vod_id": "123"}),
    ]

    should_not_match = [
        "https://www.aloula.sa/en/any",
        "https://www.aloula.sa/de/any/path",
        "https://www.aloula.sa/live/",
        "https://www.aloula.sa/abc/live/slug",
        "https://www.aloula.sa/en/live/",
        "https://www.aloula.sa/episode/",
        "https://www.aloula.sa/abc/episode/123",
        "https://www.aloula.sa/en/episode/",
        "https://www.aloula.sa/episode/abc",
        "https://www.aloula.sa/de/episode/abc",
    ]
