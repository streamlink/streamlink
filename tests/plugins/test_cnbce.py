from streamlink.plugins.cnbce import CNBCE
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCNBCE(PluginCanHandleUrl):
    __plugin__ = CNBCE

    should_match = [
        "https://www.cnbce.com/canli-yayin",
    ]
