from streamlink.plugins.egame import Egame
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlEgame(PluginCanHandleUrl):
    __plugin__ = Egame

    should_match = [
        'https://egame.qq.com/497383565',
    ]

    should_not_match = [
        'https://egame.qq.com/',
        'https://egame.qq.com/livelist?layoutid=lol',
        'https://egame.qq.com/vod?videoId=123123123123123',
        'https://egame.qq.com/aaabbbb'
    ]
