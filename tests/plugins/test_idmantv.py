import unittest

from streamlink.plugins.idmantv import IdmanTV


class TestPluginIdmanTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://player.tvibo.com/aztv/5929820',
            'http://player.tvibo.com/aztv/6858270/',
            'http://player.tvibo.com/aztv/3977238/',
        ]
        for url in should_match:
            self.assertTrue(IdmanTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://www.idmantv.az/',
            'https://www.twitch.tv/twitch'
        ]
        for url in should_not_match:
            self.assertFalse(IdmanTV.can_handle_url(url))
