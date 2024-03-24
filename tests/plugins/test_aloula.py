from streamlink.plugins.aloula import Aloula
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAloula(PluginCanHandleUrl):
    __plugin__ = Aloula

    should_match_groups = [
        (("live", "https://www.aloula.sa/live/saudiatv"), {"live_slug": "saudiatv"}),
        (("live", "https://www.aloula.sa/en/live/saudiatv"), {"live_slug": "saudiatv"}),
        (("vod", "https://www.aloula.sa/episode/6676"), {"vod_id": "6676"}),
        (("vod", "https://www.aloula.sa/en/episode/6676"), {"vod_id": "6676"}),
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
