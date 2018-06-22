import unittest

from streamlink.plugins.cnews import CNEWS


class TestPluginCNEWS(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(CNEWS.can_handle_url("http://www.cnews.fr/le-direct"))
        self.assertTrue(CNEWS.can_handle_url("http://www.cnews.fr/direct"))
        self.assertTrue(CNEWS.can_handle_url("http://www.cnews.fr/emission/2018-06-12/meteo-du-12062018-784730"))
        self.assertTrue(CNEWS.can_handle_url("http://www.cnews.fr/emission/2018-06-12/le-journal-des-faits-divers-du-12062018-784704"))
        # shouldn't match
        self.assertFalse(CNEWS.can_handle_url("http://www.cnews.fr/"))
        self.assertFalse(CNEWS.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(CNEWS.can_handle_url("http://www.youtube.com/"))
