from streamlink.plugins.wwenetwork import WWENetwork
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlWWENetwork(PluginCanHandleUrl):
    __plugin__ = WWENetwork

    should_match = [
        "https://network.wwe.com/"
    ]

    should_match_groups = [
        ("https://network.wwe.com/video/3622", {"video_id": "3622"}),
    ]

