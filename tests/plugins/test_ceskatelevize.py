from streamlink.plugins.ceskatelevize import Ceskatelevize
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCeskatelevize(PluginCanHandleUrl):
    __plugin__ = Ceskatelevize

    should_match = [
        "https://www.ceskatelevize.cz/zive/ct1/",
        "https://www.ceskatelevize.cz/zive/ct2/",
        "https://www.ceskatelevize.cz/zive/ct24/",
        "https://www.ceskatelevize.cz/zive/ct26/",
        "https://www.ceskatelevize.cz/zive/ct27/",
        "https://www.ceskatelevize.cz/zive/ct28/",
        "https://www.ceskatelevize.cz/zive/ct31/",
        "https://www.ceskatelevize.cz/zive/ct32/",
        "https://www.ceskatelevize.cz/zive/decko/",
        "https://www.ceskatelevize.cz/zive/sport/",
    ]

    should_not_match = [
        "http://decko.ceskatelevize.cz/zive/",
        "http://www.ceskatelevize.cz/art/zive/",
        "http://www.ceskatelevize.cz/ct1/zive/",
        "http://www.ceskatelevize.cz/ct2/zive/",
        "http://www.ceskatelevize.cz/ct24/",
        "http://www.ceskatelevize.cz/sport/zive-vysilani/",
    ]
