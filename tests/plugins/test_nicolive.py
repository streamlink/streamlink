import unittest

from streamlink.plugins.nicolive import NicoLive


class TestPluginNicoLive(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://live2.nicovideo.jp/watch/lv534562961',
            'http://live2.nicovideo.jp/watch/lv534562961',
            'https://live.nicovideo.jp/watch/lv534562961',
            'https://live2.nicovideo.jp/watch/lv534562961?ref=rtrec&zroute=recent',
        ]
        for url in should_match:
            self.assertTrue(NicoLive.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(NicoLive.can_handle_url(url))
