from streamlink.plugins.ard_live import ARDLive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlARDLive(PluginCanHandleUrl):
    __plugin__ = ARDLive

    should_match = [
        'https://daserste.de/live/index.html',
        'https://www.daserste.de/live/index.html',
    ]

    should_not_match = [
        'http://mediathek.daserste.de/live',
    ]
