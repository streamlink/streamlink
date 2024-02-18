from streamlink.plugins.wwenetwork import WWENetwork
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlWWENetwork(PluginCanHandleUrl):
    __plugin__ = WWENetwork

    should_match_groups = [
        ("https://network.wwe.com/video/3622", {"stream_id": "3622"}),
        ("https://network.wwe.com/live/3622", {"stream_id": "3622"}),
    ]
