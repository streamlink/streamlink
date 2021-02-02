from streamlink.plugins.ceskatelevize import Ceskatelevize
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCeskatelevize(PluginCanHandleUrl):
    __plugin__ = Ceskatelevize

    should_match = [
        'http://www.ceskatelevize.cz/ct1/zive/',
        'http://www.ceskatelevize.cz/ct2/zive/',
        'http://www.ceskatelevize.cz/ct24/',
        'http://www.ceskatelevize.cz/sport/zive-vysilani/',
        'http://decko.ceskatelevize.cz/zive/',
        'http://www.ceskatelevize.cz/art/zive/',
    ]
