from streamlink.plugins.yupptv import YuppTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlYuppTV(PluginCanHandleUrl):
    __plugin__ = YuppTV

    should_match = [
        'https://www.yupptv.com/channels/etv-telugu/live',
        'https://www.yupptv.com/channels/india-today-news/news/25326023/15-jun-2018',
    ]
