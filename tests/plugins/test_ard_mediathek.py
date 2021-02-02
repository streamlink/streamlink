from streamlink.plugins.ard_mediathek import ARDMediathek
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlARDMediathek(PluginCanHandleUrl):
    __plugin__ = ARDMediathek

    should_match = [
        'http://mediathek.daserste.de/live',
        'http://www.ardmediathek.de/tv/Sportschau/'
    ]

    should_not_match = [
        'https://daserste.de/live/index.html',
        'https://www.daserste.de/live/index.html',
    ]
