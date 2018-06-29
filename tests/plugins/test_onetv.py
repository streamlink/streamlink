import unittest

from streamlink.plugins.onetv import OneTV


class TestPluginOneTV(unittest.TestCase):
    def test_can_handle_url(self):
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
        for url in should_match:
            self.assertTrue(OneTV.can_handle_url(url))

        should_not_match = [
            "https://www.youtube.com",
        ]
        for url in should_not_match:
            self.assertFalse(OneTV.can_handle_url(url))

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

        self.assertEqual(OneTV("https://www.ctclove.ru/online").live_api_url,
                         "https://media.1tv.ru/api/v1/ctc/playlist/ctc-love_as_array.json")

        self.assertEqual(OneTV("http://domashny.ru/online").live_api_url,
                         "http://media.1tv.ru/api/v1/ctc/playlist/ctc-dom_as_array.json")
