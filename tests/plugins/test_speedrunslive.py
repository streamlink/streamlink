import unittest

from streamlink.plugins.speedrunslive import SpeedRunsLive


class TestPluginSpeedRunsLive(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.speedrunslive.com/#!/twitch',
        ]
        for url in should_match:
            self.assertTrue(SpeedRunsLive.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.twitch.tv',
        ]
        for url in should_not_match:
            self.assertFalse(SpeedRunsLive.can_handle_url(url))
