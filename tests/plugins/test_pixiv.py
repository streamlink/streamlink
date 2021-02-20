from streamlink.plugins.pixiv import Pixiv
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPixiv(PluginCanHandleUrl):
    __plugin__ = Pixiv

    should_match = [
        'https://sketch.pixiv.net/@exampleuser',
        'https://sketch.pixiv.net/@exampleuser/lives/000000000000000000',
    ]

    should_not_match = [
        'https://sketch.pixiv.net',
    ]
