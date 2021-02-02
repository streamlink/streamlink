from streamlink.plugins.tga import Tga
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTga(PluginCanHandleUrl):
    __plugin__ = Tga

    should_match = [
        'http://star.longzhu.com/lpl',
        'http://y.longzhu.com/y123123?from=tonglan2.1',
        'http://star.longzhu.com/123123?from=tonglan4.3',
    ]
