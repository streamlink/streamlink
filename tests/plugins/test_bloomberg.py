from streamlink.plugins.bloomberg import Bloomberg
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBloomberg(PluginCanHandleUrl):
    __plugin__ = Bloomberg

    should_match = [
        "https://www.bloomberg.com/live/us",
        "https://www.bloomberg.com/live/europe",
        "https://www.bloomberg.com/live/asia",
        "https://www.bloomberg.com/live/stream",
        "https://www.bloomberg.com/live/emea",
        "https://www.bloomberg.com/live/asia_stream",
        "https://www.bloomberg.com/news/videos/2017-04-17/wozniak-science-fiction-finally-becoming-reality-video",
        "http://www.bloomberg.com/news/videos/2017-04-17/russia-s-stake-in-a-u-s-north-korea-conflict-video"
    ]

    should_not_match = [
        "https://www.bloomberg.com/live/",
        "https://www.bloomberg.com/politics/articles/2017-04-17/french-race-up-for-grabs-days-before-voters-cast-first-ballots",
    ]
