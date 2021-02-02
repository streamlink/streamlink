from streamlink.plugins.nbc import NBC
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNBC(PluginCanHandleUrl):
    __plugin__ = NBC

    should_match = [
        'https://www.nbc.com/nightly-news/video/nbc-nightly-news-jun-29-2018/3745314',
    ]
