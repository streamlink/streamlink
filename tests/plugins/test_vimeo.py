from streamlink.plugins.vimeo import Vimeo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVimeo(PluginCanHandleUrl):
    __plugin__ = Vimeo

    should_match = [
        "https://vimeo.com/237163735",
        "https://vimeo.com/channels/music/176894130",
        "https://vimeo.com/album/3706071/video/148903960",
        "https://vimeo.com/ondemand/surveyopenspace/92630739",
        "https://vimeo.com/ondemand/100footsurfingdays",
        "https://player.vimeo.com/video/176894130",
    ]

    should_not_match = [
        "https://www.vimeo.com/"
    ]
