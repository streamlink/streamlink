from streamlink.plugins.okru import OKru
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOKru(PluginCanHandleUrl):
    __plugin__ = OKru

    should_match = [
        'https://ok.ru/live/12345',
        'http://ok.ru/live/12345',
        'http://www.ok.ru/live/12345',
        'https://ok.ru/video/266205792931',
    ]
