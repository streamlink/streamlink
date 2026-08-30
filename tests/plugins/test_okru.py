from streamlink.plugins.okru import OKru
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOKru(PluginCanHandleUrl):
    __plugin__ = OKru

    should_match = [
        ("default", "https://ok.ru/live/ID"),
        ("default", "https://ok.ru/video/ID"),
        ("default", "https://ok.ru/videoembed/ID"),
        ("default", "https://www.ok.ru/video/ID"),
        ("mobile", "https://m.ok.ru/video/ID"),
        ("mobile", "https://mobile.ok.ru/video/ID"),
    ]
