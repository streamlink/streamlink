from streamlink.plugins.linelive import LineLive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLineLive(PluginCanHandleUrl):
    __plugin__ = LineLive

    should_match = [
        'http://live.line.me/channels/123/broadcast/12345678',
        'https://live.line.me/channels/123/broadcast/12345678',
    ]

    should_not_match = [
        'https://live.line.me/channels/123/upcoming/12345678',
    ]
