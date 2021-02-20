from streamlink.plugins.viutv import ViuTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlViuTV(PluginCanHandleUrl):
    __plugin__ = ViuTV

    should_match = [
        "https://viu.tv/ch/99"
    ]

    should_not_match = [
        "https://viu.tv/encore/king-maker-ii/king-maker-iie4fuk-hei-baan-hui-ji-on-ji-sun-dang-cheung"
    ]
