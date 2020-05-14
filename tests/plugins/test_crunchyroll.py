import unittest

from streamlink.plugins.crunchyroll import Crunchyroll


class TestPluginCrunchyroll(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.crunchyroll.com/idol-incidents/episode-1-why-become-a-dietwoman-728233",
            "http://www.crunchyroll.com/ru/idol-incidents/episode-1-why-become-a-dietwoman-728233",
            "http://www.crunchyroll.com/idol-incidents/media-728233",
            "http://www.crunchyroll.com/fr/idol-incidents/media-728233",
            "http://www.crunchyroll.com/media-728233",
            "http://www.crunchyroll.com/de/media-728233",
            "http://www.crunchyroll.fr/media-728233",
            "http://www.crunchyroll.fr/es/media-728233"
        ]
        for url in should_match:
            self.assertTrue(Crunchyroll.can_handle_url(url))

        should_not_match = [
            "http://www.crunchyroll.com/gintama",
            "http://www.crunchyroll.es/gintama",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(Crunchyroll.can_handle_url(url))
