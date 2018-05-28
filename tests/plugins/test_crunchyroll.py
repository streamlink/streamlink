import unittest

from streamlink.plugins.crunchyroll import Crunchyroll


class TestPluginCrunchyroll(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Crunchyroll.can_handle_url("http://www.crunchyroll.com/idol-incidents/episode-1-why-become-a-dietwoman-728233"))
        self.assertTrue(Crunchyroll.can_handle_url("http://www.crunchyroll.com/idol-incidents/media-728233"))
        self.assertTrue(Crunchyroll.can_handle_url("http://www.crunchyroll.com/media-728233"))
        self.assertTrue(Crunchyroll.can_handle_url("http://www.crunchyroll.fr/media-728233"))

        # shouldn't match
        self.assertFalse(Crunchyroll.can_handle_url("http://www.crunchyroll.com/gintama"))
        self.assertFalse(Crunchyroll.can_handle_url("http://www.crunchyroll.es/gintama"))
        self.assertFalse(Crunchyroll.can_handle_url("http://www.youtube.com/"))
