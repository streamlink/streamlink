import unittest

from streamlink.plugins.onetv import OneTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOneTV(PluginCanHandleUrl):
    __plugin__ = OneTV

    should_match = [
        "https://www.1tv.ru/live",
        "http://www.1tv.ru/live",
        "http://www.1tv.ru/some-show/some-programme-2018-03-10",
        "https://www.ctc.ru/online",
        "http://www.ctc.ru/online",
        "https://www.chetv.ru/online",
        "http://www.chetv.ru/online",
        "https://www.ctclove.ru/online",
        "http://www.ctclove.ru/online",
        "https://www.domashny.ru/online"
        "http://www.domashny.ru/online"
    ]


class TestPluginOneTV(unittest.TestCase):
    def test_channel(self):
        self.assertEqual(OneTV("http://1tv.ru/live").channel,
                         "1tv")
        self.assertEqual(OneTV("http://www.ctclove.ru/online").channel,
                         "ctc-love")
        self.assertEqual(OneTV("http://domashny.ru/online").channel,
                         "ctc-dom")

    def test_live_api_url(self):
        self.assertEqual(OneTV("http://1tv.ru/live").live_api_url,
                         "http://stream.1tv.ru/api/playlist/1tvch_as_array.json")
