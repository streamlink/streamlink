from streamlink.plugins.nbcnews import NBCNews
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNBCNews(PluginCanHandleUrl):
    __plugin__ = NBCNews

    should_match = [
        'https://www.nbcnews.com/now/',
        'http://www.nbcnews.com/now/'
    ]

    should_not_match = [
        'https://www.nbcnews.com/',
        'http://www.nbcnews.com/'
    ]
