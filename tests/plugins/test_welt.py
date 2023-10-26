from streamlink.plugins.welt import Welt
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlWelt(PluginCanHandleUrl):
    __plugin__ = Welt

    should_match = [
        "https://welt.de/tv-programm-live-stream/",
        "https://www.welt.de/tv-programm-live-stream/",
        "https://www.welt.de/tv-programm-n24-doku/",
        "https://www.welt.de/mediathek/dokumentation/space/strip-the-cosmos/sendung192055593/Strip-the-Cosmos-Die-Megastuerme-der-Planeten.html",
        "https://www.welt.de/mediathek/magazin/gesellschaft/sendung247758214/Die-Welt-am-Wochenende-Auf-hoher-See-mit-der-Gorch-Fock.html",
    ]
