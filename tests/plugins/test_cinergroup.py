from streamlink.plugins.cinergroup import CinerGroup
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCinerGroup(PluginCanHandleUrl):
    __plugin__ = CinerGroup

    should_match = [
        "https://showtv.com.tr/canli-yayin",
        "https://showtv.com.tr/canli-yayin/showtv",
        "https://haberturk.com/canliyayin",
        "https://haberturk.com/tv/canliyayin",
        "http://haberturk.tv/canliyayin",
        "http://showmax.com.tr/canliyayin",
        "https://showturk.com.tr/canli-yayin/showturk",
    ]
