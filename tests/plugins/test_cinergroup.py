from streamlink.plugins.cinergroup import CinerGroup
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCinerGroup(PluginCanHandleUrl):
    __plugin__ = CinerGroup

    should_match = [
        'http://showtv.com.tr/canli-yayin',
        'http://haberturk.com/canliyayin',
        'http://showmax.com.tr/canliyayin',
        'http://showturk.com.tr/canli-yayin/showturk',
        'http://bloomberght.com/tv',
        'http://haberturk.tv/canliyayin',
    ]
