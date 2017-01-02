import unittest

from streamlink.plugins.pluzz import Pluzz


class TestPluginPluzz(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Pluzz.can_handle_url("http://pluzz.francetv.fr/france2"))
        self.assertTrue(Pluzz.can_handle_url("http://pluzz.francetv.fr/france3"))
        self.assertTrue(Pluzz.can_handle_url("http://pluzz.francetv.fr/france3-franche-comte"))
        self.assertTrue(Pluzz.can_handle_url("http://pluzz.francetv.fr/france4"))
        self.assertTrue(Pluzz.can_handle_url("http://pluzz.francetv.fr/france5"))
        self.assertTrue(Pluzz.can_handle_url("http://pluzz.francetv.fr/franceo"))
        self.assertTrue(Pluzz.can_handle_url("http://pluzz.francetv.fr/franceinfo"))
        self.assertTrue(Pluzz.can_handle_url("http://pluzz.francetv.fr/videos/jt20h.html"))
        self.assertTrue(Pluzz.can_handle_url("http://pluzz.francetv.fr/videos/jt_1213_franche_comte.html"))

        # shouldn't match
        self.assertFalse(Pluzz.can_handle_url("http://pluzz.francetv.fr/"))
        self.assertFalse(Pluzz.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Pluzz.can_handle_url("http://www.youtube.com/"))
