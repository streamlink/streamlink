import unittest

from streamlink.plugins.goodgame import GoodGame


class TestPluginGoodGame(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://goodgame.ru/channel/ABC_ABC/#autoplay',
            'https://goodgame.ru/channel/ABC123ABC/#autoplay',
            'https://goodgame.ru/channel/ABC/#autoplay',
            'https://goodgame.ru/channel/123ABC123/#autoplay',
        ]
        for url in should_match:
            self.assertTrue(GoodGame.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(GoodGame.can_handle_url(url))
