from streamlink.plugins.bigo import Bigo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBigo(PluginCanHandleUrl):
    __plugin__ = Bigo

    should_match = [
        "http://bigo.tv/00000000",
        "https://bigo.tv/00000000",
        "https://www.bigo.tv/00000000",
        "http://www.bigo.tv/00000000",
        "http://www.bigo.tv/fancy1234",
        "http://www.bigo.tv/abc.123",
        "http://www.bigo.tv/000000.00",
    ]

    should_not_match = [
        # Old URLs don't work anymore
        "http://live.bigo.tv/00000000",
        "https://live.bigo.tv/00000000",
        "http://www.bigoweb.co/show/00000000",
        "https://www.bigoweb.co/show/00000000",
        "http://bigoweb.co/show/00000000",
        "https://bigoweb.co/show/00000000",

        # Wrong URL structure
        "https://www.bigo.tv/show/00000000",
        "http://www.bigo.tv/show/00000000",
        "http://bigo.tv/show/00000000",
        "https://bigo.tv/show/00000000",
    ]
