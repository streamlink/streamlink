import unittest

from streamlink.plugins.egame import Egame


class TestPluginEgame(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://egame.qq.com/497383565',
        ]
        for url in should_match:
            self.assertTrue(Egame.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
            'https://egame.qq.com/404.html'
        ]
        for url in should_not_match:
            self.assertFalse(Egame.can_handle_url(url))
