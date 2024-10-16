from streamlink.plugins.soop import Soop
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSoop(PluginCanHandleUrl):
    __plugin__ = Soop

    should_match = [
        "http://play.sooplive.co.kr/exampleuser",
        "http://play.sooplive.co.kr/exampleuser/123123123",
        "https://play.sooplive.co.kr/exampleuser",
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
