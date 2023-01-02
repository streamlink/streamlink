from streamlink.plugins.ceskatelevize import Ceskatelevize
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCeskatelevize(PluginCanHandleUrl):
    __plugin__ = Ceskatelevize

    should_match = [
        "https://ceskatelevize.cz/zive/any",
        "https://www.ceskatelevize.cz/zive/any",
        "https://ct24.ceskatelevize.cz/",
        "https://ct24.ceskatelevize.cz/any",
        "https://decko.ceskatelevize.cz/",
        "https://decko.ceskatelevize.cz/any",
        "https://sport.ceskatelevize.cz/",
        "https://sport.ceskatelevize.cz/any",
    ]

    should_not_match = [
        "https://ceskatelevize.cz/",
        "https://www.ceskatelevize.cz/zive/",
    ]
