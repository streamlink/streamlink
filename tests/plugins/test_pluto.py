import unittest

from streamlink.plugins.pluto import Pluto


class TestPluginPluto(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Pluto.can_handle_url("http://www.pluto.tv/live-tv/channel-lineup"))
        self.assertTrue(Pluto.can_handle_url("http://pluto.tv/live-tv/nfl-channel"))
        self.assertTrue(Pluto.can_handle_url("https://pluto.tv/live-tv/red-bull-tv-2"))
        self.assertTrue(Pluto.can_handle_url("https://pluto.tv/live-tv/4k-tv"))
        self.assertTrue(Pluto.can_handle_url("http://www.pluto.tv/on-demand/series/leverage/season/1/episode/the-nigerian-job-2009-1-1"))
        self.assertTrue(Pluto.can_handle_url("http://pluto.tv/on-demand/series/fear-factor-usa-(lf)/season/5/episode/underwater-safe-savetongue-bob-and-transfertruck-car-ramp-2004-5-3"))
        self.assertTrue(Pluto.can_handle_url("https://www.pluto.tv/on-demand/movies/dr.-no-1963-1-1"))
        self.assertTrue(Pluto.can_handle_url("http://pluto.tv/on-demand/movies/the-last-dragon-(1985)-1-1"))

        # shouldn't match
        self.assertFalse(Pluto.can_handle_url("https://fake.pluto.tv/live-tv/hello"))
        self.assertFalse(Pluto.can_handle_url("http://www.pluto.tv/live-tv/channel-lineup/extra"))
        self.assertFalse(Pluto.can_handle_url("https://www.pluto.tv/live-tv"))
        self.assertFalse(Pluto.can_handle_url("https://pluto.tv/live-tv"))
        self.assertFalse(Pluto.can_handle_url("https://www.pluto.com/live-tv/swag"))
        self.assertFalse(Pluto.can_handle_url("https://youtube.com/live-tv/swag.html"))
        self.assertFalse(Pluto.can_handle_url("http://pluto.tv/movies/dr.-no-1963-1-1"))
        self.assertFalse(Pluto.can_handle_url("http://pluto.tv/on-demand/movies/dr.-no-1/963-1-1"))
        self.assertFalse(Pluto.can_handle_url("http://pluto.tv/on-demand/series/dr.-no-1963-1-1"))
        self.assertFalse(Pluto.can_handle_url("http://pluto.tv/on-demand/movies/leverage/season/1/episode/the-nigerian-job-2009-1-1"))
        self.assertFalse(Pluto.can_handle_url("http://pluto.tv/on-demand/fear-factor-usa-(lf)/season/5/episode/underwater-safe-savetongue-bob-and-transfertruck-car-ramp-2004-5-3"))


if __name__ == "__main__":
    unittest.main()
