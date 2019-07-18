import unittest

from streamlink.plugins.beattv import BeatTV


class TestPluginBeatTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://be-at.tv/video/adam_beyer_hyte_nye_germany_2018',
            'https://www.be-at.tv/videos/ben-klock-great-wall-festival-2019'
        ]
        for url in should_match:
            self.assertTrue(BeatTV.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
            'https://www.be-at.tv/series/extrema-outdoor-belgium-2019'
        ]
        for url in should_not_match:
            self.assertFalse(BeatTV.can_handle_url(url))
