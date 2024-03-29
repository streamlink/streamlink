from streamlink.plugins.bloomberg import Bloomberg
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBloomberg(PluginCanHandleUrl):
    __plugin__ = Bloomberg

    should_match_groups = [
        (
            ("live", "https://www.bloomberg.com/live"),
            {},
        ),
        (
            ("live", "https://www.bloomberg.com/live/europe"),
            {"channel": "europe"},
        ),
        (
            ("live", "https://www.bloomberg.com/live/us"),
            {"channel": "us"},
        ),
        (
            ("vod", "https://www.bloomberg.com/news/videos/2022-08-10/-bloomberg-surveillance-early-edition-full-08-10-22"),
            {},
        ),
    ]

    should_not_match = [
        "https://www.bloomberg.com/politics/articles/2017-04-17/french-race-up-for-grabs-days-before-voters-cast-first-ballots",
    ]
