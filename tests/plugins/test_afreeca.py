from streamlink.plugins.afreeca import AfreecaTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAfreecaTV(PluginCanHandleUrl):
    __plugin__ = AfreecaTV

    should_match = [
        "http://play.afreecatv.com/exampleuser",
        "http://play.afreecatv.com/exampleuser/123123123",
        "https://play.afreecatv.com/exampleuser",
    ]

    should_not_match = [
        "http://afreeca.com/exampleuser",
        "http://afreeca.com/exampleuser/123123123",
        "http://afreecatv.com/exampleuser",
        "http://afreecatv.com/exampleuser/123123123",
        "http://www.afreecatv.com.tw",
        "http://www.afreecatv.jp",
    ]
