from streamlink.plugins.lura import Lura
from tests.plugins import PluginCanHandleUrl

class TestPluginCanHandleUrlLura(PluginCanHandleUrl):
    __plugin__ = Lura

    should_match = [
        'https://w3.mp.lura.live/player/prod/v3/anvload.html?key=somekey',
        'http://w3.mp.lura.live/player/prod/v3/anvload.html?key=somekey',
    ]

    should_not_match = [
        'https://tkx.mp.lura.live/rest/v2/mcp/video',
    ]
