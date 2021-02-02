from streamlink.plugins.zeenews import ZeeNews
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlZeeNews(PluginCanHandleUrl):
    __plugin__ = ZeeNews

    should_match = [
        'https://zeenews.india.com/live-tv',
        'https://zeenews.india.com/live-tv/embed',
    ]
