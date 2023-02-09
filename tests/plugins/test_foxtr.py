from streamlink.plugins.foxtr import FoxTR
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlFoxTR(PluginCanHandleUrl):
    __plugin__ = FoxTR

    should_match = [
        "http://www.fox.com.tr/canli-yayin",
    ]
