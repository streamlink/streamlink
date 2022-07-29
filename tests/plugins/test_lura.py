from streamlink.plugins.lura import Lura
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLura(PluginCanHandleUrl):

    __plugin__ = Lura

    should_match_groups = [
        ("https://w3.mp.lura.live/player/prod/v3/anvload.html?key=somekey", {"params": "key=somekey"}),
        ("http://w3.mp.lura.live/player/prod/v3/anvload.html?key=somekey", {"params": "key=somekey"}),
    ]
