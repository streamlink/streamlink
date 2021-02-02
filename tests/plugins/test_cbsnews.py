from streamlink.plugins.cbsnews import CBSNews
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCBSNews(PluginCanHandleUrl):
    __plugin__ = CBSNews

    should_match = [
        "https://www.cbsnews.com/live/cbs-sports-hq/",
        "https://www.cbsnews.com/live/cbsn-local-bay-area/",
        "https://www.cbsnews.com/live/",
    ]

    should_not_match = [
        "https://www.cbsnews.com/feature/election-2020/",
        "https://www.cbsnews.com/48-hours/",
    ]
