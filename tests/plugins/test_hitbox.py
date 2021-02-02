from streamlink.plugins.hitbox import Hitbox
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHitbox(PluginCanHandleUrl):
    __plugin__ = Hitbox

    should_match = [
        'http://www.smashcast.tv/pixelradio',
        'https://www.hitbox.tv/pixelradio',
        'https://www.smashcast.tv/jurnalfm',
        'https://www.smashcast.tv/sscaitournament',
    ]
