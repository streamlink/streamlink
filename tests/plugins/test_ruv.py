from streamlink.plugins.ruv import Ruv
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRuv(PluginCanHandleUrl):
    __plugin__ = Ruv

    should_match = [
        "http://ruv.is/ruv",
        "http://ruv.is/ruv",
        "http://ruv.is/ruv/",
        "https://ruv.is/ruv/",
        "http://www.ruv.is/ruv",
        "http://www.ruv.is/ruv/",
        "http://ruv.is/ruv2",
        "http://ruv.is/ras1",
        "http://ruv.is/ras2",
        "http://ruv.is/rondo",
        "http://www.ruv.is/spila/ruv/ol-2018-ishokki-karla/20180217",
        "http://www.ruv.is/spila/ruv/frettir/20180217",
    ]

    should_not_match = [
        "http://ruv.is/ruvnew",
    ]
