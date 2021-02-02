from streamlink.plugins.tvp import TVP
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVP(PluginCanHandleUrl):
    __plugin__ = TVP

    should_match = [
        'http://tvpstream.vod.tvp.pl/?channel_id=14327511',
        'http://tvpstream.vod.tvp.pl/?channel_id=1455',
    ]

    should_not_match = [
        'http://tvp.pl/',
        'http://vod.tvp.pl/',
    ]
