from streamlink.plugins.wwenetwork import WWENetwork
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlWWENetwork(PluginCanHandleUrl):
    __plugin__ = WWENetwork

    should_match = [
        "https://watch.wwe.com/in-ring/3622",
    ]
