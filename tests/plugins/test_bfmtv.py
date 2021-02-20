from streamlink.plugins.bfmtv import BFMTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBFMTV(PluginCanHandleUrl):
    __plugin__ = BFMTV

    should_match = [
        "https://www.bfmtv.com/mediaplayer/live-video/",
        "https://bfmbusiness.bfmtv.com/mediaplayer/live-video/",
        "https://www.bfmtv.com/mediaplayer/live-bfm-paris/",
        "https://rmc.bfmtv.com/mediaplayer/live-audio/",
        "https://rmcsport.bfmtv.com/mediaplayer/live-bfm-sport/",
        "https://rmcdecouverte.bfmtv.com/mediaplayer-direct/",
        "https://www.bfmtv.com/mediaplayer/replay/premiere-edition/",
        "https://bfmbusiness.bfmtv.com/mediaplayer/replay/good-morning-business/",
        "https://rmc.bfmtv.com/mediaplayer/replay/les-grandes-gueules/",
        "https://rmc.bfmtv.com/mediaplayer/replay/after-foot/",
        "https://www.01net.com/mediaplayer/replay/jtech/",
        "https://www.bfmtv.com/politique/macron-et-le-pen-talonnes-par-fillon-et-melenchon-a-l-approche"
        + "-du-premier-tour-1142070.html",
        "https://rmcdecouverte.bfmtv.com/mediaplayer-replay/?id=6714&title=TOP%20GEAR%20:PASSION%20VINTAGE"
    ]
