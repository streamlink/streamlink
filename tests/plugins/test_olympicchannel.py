import unittest

from streamlink.plugins.olympicchannel import OlympicChannel


class TestPluginOlympicChannel(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(OlympicChannel.can_handle_url("https://www.olympicchannel.com/en/playback/listen-up-olympic-dreamers/"))
        self.assertTrue(OlympicChannel.can_handle_url("https://www.olympicchannel.com/en/tv/overflow-6/"))
        self.assertTrue(OlympicChannel.can_handle_url("https://www.olympicchannel.com/en/tv/livestream-5/"))

        # shouldn't match
        self.assertFalse(OlympicChannel.can_handle_url("https://www.olympicchannel.com/en/"))
        self.assertFalse(OlympicChannel.can_handle_url("https://www.olympicchannel.com/en/channel/olympic-channel/"))
