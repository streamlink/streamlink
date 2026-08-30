from streamlink.plugins.ceskatelevize import Ceskatelevize
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCeskatelevize(PluginCanHandleUrl):
    __plugin__ = Ceskatelevize

    should_match_groups = [
        (("channel", "https://ct24.ceskatelevize.cz/"), {"channel": "ct24"}),
        (("channel", "https://decko.ceskatelevize.cz/"), {"channel": "decko"}),
        (("sport", "https://sport.ceskatelevize.cz/"), {}),
        (("default", "https://ceskatelevize.cz/zive/ct1"), {}),
        (("default", "https://ceskatelevize.cz/zive/ct2"), {}),
        (("default", "https://ceskatelevize.cz/zive/art"), {}),
        (("default", "https://ceskatelevize.cz/zive/ch-28"), {}),
    ]

    should_not_match = [
        "https://ceskatelevize.cz/",
        "https://www.ceskatelevize.cz/zive/",
    ]
