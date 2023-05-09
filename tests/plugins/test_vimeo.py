from streamlink.plugins.vimeo import Vimeo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVimeo(PluginCanHandleUrl):
    __plugin__ = Vimeo

    should_match = [
        ("default", "https://vimeo.com/783455878"),
        ("default", "https://vimeo.com/channels/music/176894130"),
        ("default", "https://vimeo.com/album/3706071/video/148903960"),
        ("default", "https://vimeo.com/ondemand/worldoftomorrow3/467204924"),
        ("default", "https://vimeo.com/ondemand/100footsurfingdays"),
        ("default", "https://vimeo.com/771745400/840d05200c"),
        ("player", "https://player.vimeo.com/video/176894130"),
    ]

    should_not_match = [
        "https://www.vimeo.com/",
    ]
