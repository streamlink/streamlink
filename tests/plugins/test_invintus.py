import unittest

from streamlink.plugins.invintus import InvintusMedia


class TestPluginInvintusMedia(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://player.invintus.com/?clientID=9375922947&eventID=2020031185',
            'https://player.invintus.com/?clientID=9375922947&eventID=2020031184',
            'https://player.invintus.com/?clientID=9375922947&eventID=2020031183',
            'https://player.invintus.com/?clientID=9375922947&eventID=2020031182',
            'https://player.invintus.com/?clientID=9375922947&eventID=2020031181'
        ]
        for url in should_match:
            self.assertTrue(InvintusMedia.can_handle_url(url))

        self.assertFalse(InvintusMedia.can_handle_url("https://example.com"))
