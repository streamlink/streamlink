from streamlink.plugins.cinergroup import CinerGroup
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCinerGroup(PluginCanHandleUrl):
    __plugin__ = CinerGroup

    should_match_groups = [
        (("bloomberght", "https://bloomberght.com/tv"), {}),
        (("haberturk", "https://haberturk.com/canliyayin"), {}),
        (("haberturk", "https://haberturk.com/tv/canliyayin"), {}),
        (("showmax", "http://showmax.com.tr/canliyayin"), {}),
        (("showmax", "http://showmax.com.tr/canli-yayin"), {}),
        (("showturk", "https://showturk.com.tr/canli-yayin/showturk"), {}),
        (("showturk", "https://showturk.com.tr/canli-yayin"), {}),
        (("showturk", "https://showturk.com.tr/canliyayin"), {}),
        (("showtv", "https://showtv.com.tr/canli-yayin"), {}),
        (("showtv", "https://showtv.com.tr/canli-yayin/showtv"), {}),
    ]
