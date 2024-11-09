from streamlink.plugins.abematv import AbemaTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAbemaTV(PluginCanHandleUrl):
    __plugin__ = AbemaTV

    should_match_groups = [
        (("onair", "https://abema.tv/now-on-air/abema-news"), {"onair": "abema-news"}),
        (("onair", "https://abema.tv/now-on-air/abema-news?a=b&c=d"), {"onair": "abema-news"}),
        (("episode", "https://abema.tv/video/episode/90-1053_s99_p12"), {"episode": "90-1053_s99_p12"}),
        (("episode", "https://abema.tv/video/episode/90-1053_s99_p12?a=b&c=d"), {"episode": "90-1053_s99_p12"}),
        (("slots", "https://abema.tv/channels/everybody-anime/slots/FJcUsdYjTk1rAb"), {"slots": "FJcUsdYjTk1rAb"}),
        (("slots", "https://abema.tv/channels/abema-anime/slots/9rTULtcJFiFmM9?a=b"), {"slots": "9rTULtcJFiFmM9"}),
    ]

    should_not_match = [
        "https://www.abema.tv/now-on-air/abema-news",
        "https://www.abema.tv/now-on-air/",
        "https://abema.tv/timetable",
        "https://abema.tv/video",
        "https://abema.tv/video/title/13-47",
        "https://abema.tv/video/title/13-47?a=b",
    ]
