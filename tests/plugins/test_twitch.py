import unittest

from streamlink.plugins.twitch import Twitch


class TestPluginTwitch(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.twitch.tv/twitch',
            'https://www.twitch.tv/videos/150942279',
            'https://clips.twitch.tv/ObservantBenevolentCarabeefPhilosoraptor',
            'https://www.twitch.tv/twitch/video/292713971',
            'https://www.twitch.tv/twitch/v/292713971',
        ]
        for url in should_match:
            self.assertTrue(Twitch.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.twitch.tv',
        ]
        for url in should_not_match:
            self.assertFalse(Twitch.can_handle_url(url))
