from streamlink.plugins.kanal7 import KANAL7
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlKANAL7(PluginCanHandleUrl):
    __plugin__ = KANAL7

    should_match = [
        "https://www.kanal7.com/canli-izle",
    ]
