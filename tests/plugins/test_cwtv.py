import unittest

from streamlink.plugins.cwtv import CWTV


class TestPluginCWTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.cwtv.com/shows/the-100/the-warriors-will/?play=d7857786-f312-45d3-a63b-c36ba8401138',
            'http://www.cwtv.com/shows/the-outpost/',
            'http://www.cwtv.com/shows/the-flash/',
            'http://www.cwtv.com/shows/dcs-legends-of-tomorrow/',
        ]
        for url in should_match:
            self.assertTrue(CWTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'http://www.cwtv.com/',
            'http://www.cwtv.com/thecw/privacy-policy/',
            'https://www.twitch.tv/twitch'
        ]
        for url in should_not_match:
            self.assertFalse(CWTV.can_handle_url(url))
