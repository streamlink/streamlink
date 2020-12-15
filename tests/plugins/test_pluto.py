import unittest

from streamlink.plugins.pluto import Pluto


class TestPluginPluto(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.pluto.tv/live-tv/channel-lineup',
            'http://pluto.tv/live-tv/channel',
            'http://pluto.tv/live-tv/channel/',
            'https://pluto.tv/live-tv/red-bull-tv-2',
            'https://pluto.tv/live-tv/4k-tv',
            'http://www.pluto.tv/on-demand/series/leverage/season/1/episode/the-nigerian-job-2009-1-1',
            'http://pluto.tv/on-demand/series/fear-factor-usa-(lf)/season/5/episode/underwater-safe-bob-car-ramp-2004-5-3',
            'https://www.pluto.tv/on-demand/movies/dr.-no-1963-1-1',
            'http://pluto.tv/on-demand/movies/the-last-dragon-(1985)-1-1',
        ]
        for url in should_match:
            self.assertTrue(Pluto.can_handle_url(url), url)

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://fake.pluto.tv/live-tv/hello',
            'http://www.pluto.tv/live-tv/channel-lineup/extra',
            'https://www.pluto.tv/live-tv',
            'https://pluto.tv/live-tv',
            'https://www.pluto.com/live-tv/swag',
            'https://youtube.com/live-tv/swag.html',
            'http://pluto.tv/movies/dr.-no-1963-1-1',
            'http://pluto.tv/on-demand/movies/dr.-no-1/963-1-1',
            'http://pluto.tv/on-demand/series/dr.-no-1963-1-1',
            'http://pluto.tv/on-demand/movies/leverage/season/1/episode/the-nigerian-job-2009-1-1',
            'http://pluto.tv/on-demand/fear-factor-usa-(lf)/season/5/episode/underwater-safe-bob-car-ramp-2004-5-3',
        ]
        for url in should_not_match:
            self.assertFalse(Pluto.can_handle_url(url), url)
