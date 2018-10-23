import unittest

from streamlink.plugins.tvibo import Tvibo


class TestPluginTvibo(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://player.tvibo.com/aztv/5929820',
            'http://player.tvibo.com/aztv/6858270/',
            'http://player.tvibo.com/aztv/3977238/',
        ]
        for url in should_match:
            self.assertTrue(Tvibo.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://www.idmantv.az/',
            'https://www.twitch.tv/twitch'
        ]
        for url in should_not_match:
            self.assertFalse(Tvibo.can_handle_url(url))
