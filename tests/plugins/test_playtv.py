import unittest

from streamlink.plugins.playtv import PlayTV


class TestPluginPlayTV(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(PlayTV.can_handle_url("http://playtv.fr/television/arte"))
        self.assertTrue(PlayTV.can_handle_url("http://playtv.fr/television/arte/"))
        self.assertTrue(PlayTV.can_handle_url("http://playtv.fr/television/tv5-monde"))
        self.assertTrue(PlayTV.can_handle_url("http://playtv.fr/television/france-24-english/"))
        self.assertTrue(PlayTV.can_handle_url("http://play.tv/live-tv/9/arte"))
        self.assertTrue(PlayTV.can_handle_url("http://play.tv/live-tv/9/arte/"))
        self.assertTrue(PlayTV.can_handle_url("http://play.tv/live-tv/21/tv5-monde"))
        self.assertTrue(PlayTV.can_handle_url("http://play.tv/live-tv/50/france-24-english/"))

        # shouldn't match
        self.assertFalse(PlayTV.can_handle_url("http://playtv.fr/television/"))
        self.assertFalse(PlayTV.can_handle_url("http://playtv.fr/replay-tv/"))
        self.assertFalse(PlayTV.can_handle_url("http://play.tv/live-tv/"))
        self.assertFalse(PlayTV.can_handle_url("http://tvcatchup.com/"))
        self.assertFalse(PlayTV.can_handle_url("http://youtube.com/"))
