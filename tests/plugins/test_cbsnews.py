from streamlink.plugins.cbsnews import CBSNews
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCBSNews(PluginCanHandleUrl):
    __plugin__ = CBSNews

    should_match = [
        "https://cbsnews.com/live",
        "https://cbsnews.com/live/cbs-sports-hq",
        "https://cbsnews.com/sanfrancisco/live",
        "https://cbsnews.com/live/",
        "https://cbsnews.com/live/cbs-sports-hq/",
        "https://cbsnews.com/sanfrancisco/live/",
        "https://www.cbsnews.com/live/",
        "https://www.cbsnews.com/live/cbs-sports-hq/",
        "https://www.cbsnews.com/sanfrancisco/live/",
        "https://www.cbsnews.com/live/#x",
        "https://www.cbsnews.com/live/cbs-sports-hq/#x",
        "https://www.cbsnews.com/sanfrancisco/live/#x",
    ]

    should_not_match = [
        "https://www.cbsnews.com/feature/election-2020/",
        "https://www.cbsnews.com/48-hours/",
    ]
