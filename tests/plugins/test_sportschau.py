from streamlink.plugins.sportschau import Sportschau
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSportschau(PluginCanHandleUrl):
    __plugin__ = Sportschau

    should_match = [
        "http://www.sportschau.de/wintersport/videostream-livestream---wintersport-im-ersten-242.html",
        "https://www.sportschau.de/weitere/allgemein/video-kite-surf-world-tour-100.html",
    ]
