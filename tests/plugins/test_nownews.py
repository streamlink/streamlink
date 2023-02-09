from streamlink.plugins.nownews import NowNews
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNowNews(PluginCanHandleUrl):
    __plugin__ = NowNews

    should_match = [
        "https://news.now.com/home/live",
        "http://news.now.com/home/live",
        "https://news.now.com/home/live331a",
        "http://news.now.com/home/live331a",
    ]

    should_not_match = [
        "https://news.now.com/home/local",
        "http://media.now.com.hk/",
    ]
