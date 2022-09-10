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
        "https://www.bloomberght.com/tv",
        "http://www.bloomberght.com/tv",
        "https://bloomberght.com/tv",
        "http://bloomberght.com/tv",
        "http://showmax.com.tr/canliyayin",
        "http://showmax.com.tr/canli-yayin",
        "https://showturk.com.tr/canli-yayin/showturk",
        "https://showturk.com.tr/canli-yayin",
        "https://showturk.com.tr/canliyayin",
    ]
