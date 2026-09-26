from streamlink.plugins.youtvua import YouTVUA
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlYouTVUA(PluginCanHandleUrl):
    __plugin__ = YouTVUA

    should_match = [
        "https://youtv.ua/tv/unian-hd/",
        "https://youtv.ua/uk/tv/unian-hd/",
        "https://youtv.ua/en/tv/unian-hd/",
        "https://youtv.ua/ru/tv/unian-hd/",
    ]

    should_not_match = [
        "https://youtv.ua/",
        "https://youtv.ua/unian-hd/",
        "https://youtv.ua/uk/unian-hd/",
    ]
