from streamlink.plugins.kanal7 import Kanal7
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlKanal7(PluginCanHandleUrl):
    __plugin__ = Kanal7

    should_match = [
        "https://www.kanal7.com/canli-izle",
    ]
